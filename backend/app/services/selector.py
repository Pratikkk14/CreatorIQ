import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from app.core.config import get_pipeline_config, get_selection_config
from app.core.logging import logger
from app.models.models import VideoCandidate, Channel

class SelectorService:
    def classify_creator_sizes(self, candidates_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classifies channels into big, medium, and small buckets relative to the candidates.
        """
        if not candidates_data:
            return []
            
        sub_counts = []
        for c in candidates_data:
            sub_count = c.get("subscriber_count")
            if sub_count is not None:
                sub_counts.append(sub_count)
                
        if not sub_counts:
            # Fallback if no sub counts available
            for c in candidates_data:
                c["creator_size_bucket"] = "medium"
            return candidates_data

        # Load percentile configurations
        config = get_selection_config()
        pct = config.get("creator_size_percentiles", {"small_upper_pct": 33.3, "medium_upper_pct": 66.6})
        small_cutoff = np.percentile(sub_counts, pct.get("small_upper_pct", 33.3))
        medium_cutoff = np.percentile(sub_counts, pct.get("medium_upper_pct", 66.6))
        
        for c in candidates_data:
            sub = c.get("subscriber_count") or 0
            if sub <= small_cutoff:
                c["creator_size_bucket"] = "small"
            elif sub <= medium_cutoff:
                c["creator_size_bucket"] = "medium"
            else:
                c["creator_size_bucket"] = "big"
                
        return candidates_data

    def select_population(self, candidates: List[Dict[str, Any]], target_size: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Performs deterministic population selection.
        Input candidates list must contain:
          - video_id
          - semantic_score
          - language (optional)
          - creator_size_bucket (classified beforehand)
        
        Returns:
          - selected_members: List of selected candidate dicts
          - rejected_members: List of rejected candidate dicts (with rejection reasons)
        """
        # Load configs
        pipeline_config = get_pipeline_config()
        min_semantic = pipeline_config.get("relevance", {}).get("min_semantic_score", 0.5)
        check_lang = pipeline_config.get("relevance", {}).get("check_language", True)
        default_lang = pipeline_config.get("discovery", {}).get("default_language", "en")
        
        selection_config = get_selection_config()
        ratios = selection_config.get("soft_ratio", {"big": 0.3, "medium": 0.4, "small": 0.3})
        
        valid_candidates = []
        rejected_members = []
        
        # Phase 1: Filter by metadata/language/relevance
        for c in candidates:
            # Clone candidate dict to avoid side-effects
            cand = dict(c)
            cand["evaluated_at"] = datetime.now(timezone.utc)
            
            # Language validation
            lang = cand.get("language")
            if check_lang and lang and lang != default_lang:
                cand["selection_status"] = "invalid"
                cand["rejection_reason"] = "language_mismatch"
                rejected_members.append(cand)
                continue
                
            # Semantic score validation
            score = cand.get("semantic_score")
            if score is None or score < min_semantic:
                cand["selection_status"] = "rejected"
                cand["rejection_reason"] = "semantic_below_threshold"
                rejected_members.append(cand)
                continue
                
            # Valid candidate
            valid_candidates.append(cand)
            
        if not valid_candidates:
            return [], rejected_members

        # Phase 2: Stratified Selection (Soft Objectives)
        # Calculate target slots per bucket
        slots = {}
        allocated_count = 0
        
        # Sort buckets to process (big, medium, small)
        buckets = ["big", "medium", "small"]
        for b in buckets:
            ratio = ratios.get(b, 0.3)
            # Allocate slots deterministically
            slots[b] = int(np.floor(target_size * ratio))
            allocated_count += slots[b]
            
        # Distribute remaining slots to medium first, then big, then small
        remaining_slots = target_size - allocated_count
        if remaining_slots > 0:
            slots["medium"] += 1
            remaining_slots -= 1
        if remaining_slots > 0:
            slots["big"] += 1
            remaining_slots -= 1
        if remaining_slots > 0:
            slots["small"] += 1

        # Group valid candidates by bucket
        by_bucket = {b: [] for b in buckets}
        for cand in valid_candidates:
            bucket = cand.get("creator_size_bucket", "medium")
            if bucket not in by_bucket:
                bucket = "medium"
            by_bucket[bucket].append(cand)
            
        # Sort each bucket by semantic score descending
        for b in buckets:
            by_bucket[b].sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)

        selected_members = []
        borrow_pool = []
        
        # Select from each bucket up to its slot limit
        for b in buckets:
            limit = slots[b]
            bucket_candidates = by_bucket[b]
            
            selected_from_bucket = bucket_candidates[:limit]
            leftovers = bucket_candidates[limit:]
            
            selected_members.extend(selected_from_bucket)
            borrow_pool.extend(leftovers)
            
        # If we need more to reach target_size (because some buckets were short of candidates)
        needed = target_size - len(selected_members)
        if needed > 0 and borrow_pool:
            # Sort borrow pool by semantic score descending
            borrow_pool.sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)
            borrow_selected = borrow_pool[:needed]
            borrow_rejected = borrow_pool[needed:]
            
            selected_members.extend(borrow_selected)
            # Rejection reason for leftovers in borrow pool
            for r in borrow_rejected:
                r["selection_status"] = "rejected"
                r["rejection_reason"] = "population_limit_exceeded"
                rejected_members.append(r)
        else:
            # Reject all leftovers
            for r in borrow_pool:
                r["selection_status"] = "rejected"
                r["rejection_reason"] = "population_limit_exceeded"
                rejected_members.append(r)
                
        # Assign rank and selection status
        selected_members.sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)
        for idx, s in enumerate(selected_members):
            s["selection_status"] = "selected"
            s["selection_rank"] = idx + 1
            s["selection_score"] = s["semantic_score"]
            
        return selected_members, rejected_members
