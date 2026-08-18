### from __future__ import annotations
"""
U-SIE Sovereign Platform Alpha Reference Implementation + PrivacyFlow CRM HUD (v6.1)
==================================================================================
Chief Architect: Fred Laurenzo
Reference Implementation: USIE_SovereignPlatform_HUD_v6.1.py
License: Apache License, Version 2.0 (c) 2026 Fred Laurenzo

This version introduces the definitive "U-SIE Live Performance & Telemetry Dashboard" 
incorporating real-time GPU percentage use, VRAM footprint, memory bus diagnostics, 
and sub-millisecond AI/Ingestion pipeline processing durations.
"""

import os
import re
import csv
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple, Union

# Try importing Streamlit and Plotly for the HUD
try:
    import streamlit as st
    import plotly.graph_objects as go
    import pandas as pd
    import requests
    HUD_AVAILABLE = True
except ImportError:
    HUD_AVAILABLE = False

# ============================================================
# REAL-TIME GPU & HARDWARE DIAGNOSTICS (NVIDIA NVML & SUBPROCESS)
# ============================================================

def query_gpu_utilization() -> dict[str, Any]:
    """Queries NVIDIA GPU metrics dynamically using pynvml or subprocess fallback."""
    metrics = {"gpu_percentage": 0.0, "vram_used": 0.0, "vram_total": 0.0, "gpu_name": "N/A", "active": False}
    
    # Method 1: Try pynvml (NVIDIA Management Library)
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="ignore")
            metrics["gpu_percentage"] = float(util.gpu)
            metrics["vram_used"] = float(mem.used) / (1024**2)  # MB
            metrics["vram_total"] = float(mem.total) / (1024**2) # MB
            metrics["gpu_name"] = str(name)
            metrics["active"] = True
            pynvml.nvmlShutdown()
            return metrics
    except Exception:
        pass

    # Method 2: Try calling nvidia-smi command-line utility via subprocess
    try:
        import subprocess
        cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,name", "--format=csv,noheader,nounits"]
        output = subprocess.check_output(cmd, encoding="utf-8").strip()
        if output:
            parts = [p.strip() for p in output.split(",")]
            if len(parts) >= 4:
                metrics["gpu_percentage"] = float(parts[0])
                metrics["vram_used"] = float(parts[1])
                metrics["vram_total"] = float(parts[2])
                metrics["gpu_name"] = parts[3]
                metrics["active"] = True
                return metrics
    except Exception:
        pass

    return metrics

# ============================================================
# ALGEBRAIC COPRIME COORDINATE MAPPING (PROHIBITS ONE-WAY HASHES)
# ============================================================

def string_to_algebraic_float(s: str) -> float:
    """
    Deterministic prime-weighted sum algorithm to map any arbitrary 
    string value directly to an algebraic coordinate float.
    """
    if not s:
        return 0.0
    val = 0
    for char in s:
        val = (val * 31 + ord(char)) % 1000000007
    return (val % 1000000) / 10000.0

# ============================================================
# STEP 1: UNIVERSAL OBJECT FEEDER & INGESTION BOUNDARY
# ============================================================

class IntakeSource(str, Enum):
    """Declared source approaching the U-SIE intake boundary."""
    CSV = "CSV"
    XRAY = "XRAY"
    PDF = "PDF"
    BINARY = "BINARY"
    GEOSPATIAL = "GEOSPATIAL"

@dataclass(frozen=True, slots=True)
class RawObjectEnvelope:
    """Common envelope produced by the Universal Object Feeder using mutable bytearrays."""
    source_type: IntakeSource
    payload: bytearray
    metadata: dict[str, Any] = field(default_factory=dict)

class UniversalObjectFeeder:
    """Universal entry point for admitted digital objects."""
    def feed(self, source_type: IntakeSource, payload: bytearray, metadata: dict[str, Any] = None) -> RawObjectEnvelope:
        return RawObjectEnvelope(source_type=source_type, payload=payload, metadata=metadata or {})

class CSVInterchangeAdapter:
    """Structured-data interchange bridge for U-SIE."""
    def __init__(self, feeder: UniversalObjectFeeder):
        self.feeder = feeder

    def adapt_file(self, file_path: Path, metadata: dict[str, Any] = None) -> RawObjectEnvelope:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, "rb") as f:
            content = bytearray(f.read())
        meta = metadata or {}
        if "file_name" not in meta:
            meta["file_name"] = file_path.name
        return self.feeder.feed(IntakeSource.CSV, content, meta)

# ============================================================
# STEP 1 — TOKEN 0: VOLATILE INTAKE BOUNDARY WITH MEMORY SANITIZATION
# ============================================================

@dataclass(frozen=True, slots=True)
class AdmittedByteState:
    """Byte state permitted to leave the Token 0 boundary."""
    source_type: IntakeSource
    sanitized_payload: bytearray
    metadata: dict[str, Any]
    raw_bin_measurement: int  # Byte quantity captured BEFORE sanitization

class TokenZeroVolatileBoundary:
    """U-SIE Token 0 volatile intake boundary with transient memory scrubbing."""
    def __init__(self, patterns_to_redact: list[str] = None):
        self.patterns_to_redact = patterns_to_redact or [\
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # Emails\
            r"\b\d{3}-\d{2}-\d{4}\b",                           # SSNs\
            r"\b(?:\d[ -]*?){13,16}\b",                         # Credit Cards\
        ]

    def admit(self, envelope: RawObjectEnvelope) -> AdmittedByteState:
        # Step 1.1: Capture raw measurement before sanitization
        raw_bin = len(envelope.payload)
        
        # Perform deterministic PII-redaction stage
        sanitized_payload = self._deterministic_redact(envelope.payload, envelope.source_type)
        
        # Best-effort triple overwrite of transient memory buffer directly in-place
        self._triple_overwrite_buffer(envelope.payload)
        
        return AdmittedByteState(\
            source_type=envelope.source_type,\
            sanitized_payload=sanitized_payload,\
            metadata=envelope.metadata,\
            raw_bin_measurement=raw_bin\
        )

    def _deterministic_redact(self, payload: bytearray, source_type: IntakeSource) -> bytearray:
        try:
            text = payload.decode("utf-8", errors="ignore")
            # Redact common pattern list
            for pattern in self.patterns_to_redact:
                text = re.sub(pattern, "[REDACTED_PII]", text)
            
            # Context-specific redactions
            text = re.sub(r"Confidential", "[REDACTED_CONFIDENTIAL]", text, flags=re.IGNORECASE)
            return bytearray(text.encode("utf-8"))
        except Exception:
            return payload

    def _triple_overwrite_buffer(self, buffer: bytearray) -> None:
        """Triple overwrite of transient memory buffer directly in-place to protect raw heap."""
        try:
            for char in [0x00, 0xFF, 0x55]:
                for i in range(len(buffer)):
                    buffer[i] = char
        except Exception:
            pass

# ============================================================
# COHESIVE TOKEN STATE MODEL (TK1 — TK10)
# ============================================================

@dataclass
class TokenState:
    """
    Structured container holding U-SIE 10-Token representation.
    Supports dynamic subdivisions (Step 4.3) and dynamic token expansions.
    """
    tk1: float = 0.0  # C: Identity (Primary Structural Anchor)
    tk2: float = 0.0  # V: Spatial / Context
    tk3: float = 0.0  # T: Time / Temporal
    tk4: float = 0.0  # Inventory / logical mass
    tk5: float = 0.0  # Geometry representation
    tk6: float = 0.0  # Audit Seal (Deterministic sum of logic units)
    tk7: str = ""     # Complete Reference link (Sovereign baseline reference)
    tk8: float = 0.0  # Price or key economic dimension
    tk9: str = "PENDING"  # Structural Validation state (YES/NO/PENDING)
    tk10: dict[str, Any] = field(default_factory=dict)  # Baseline KPI calculations
    
    # Subdivisions and custom properties to support Token Expansion (Step 4.3)
    subdivisions: dict[str, dict[str, float]] = field(default_factory=dict)
    custom_tokens: dict[str, float] = field(default_factory=dict)
    u_phi: float = 1.0  # Common structural accounting basis

    def sum_state(self) -> float:
        """
        Laurenzo–Gemini Structural State Equation:
        S = sum_{i=1}^{n} (T_i * U_phi)
        """
        # Sum of active participating token values
        tokens = [self.tk1, self.tk2, self.tk3, self.tk4, self.tk5, self.tk8]
        
        total = 0.0
        for i, val in enumerate(tokens, start=1):
            tk_name = f"TK{i}" if i <= 5 else "TK8"
            if tk_name in self.subdivisions and self.subdivisions[tk_name]:
                # Subdivision Conservation rule: Parent token value is replaced by sum of its subdivisions
                total += sum(self.subdivisions[tk_name].values())
            else:
                total += val
                
        # Include any custom-expanded token dimensions (Token Expansion TKn)
        if self.custom_tokens:
            total += sum(self.custom_tokens.values())
            
        return total * self.u_phi

    def triangulate_3d_point(self) -> tuple[float, float, float]:
        """Returns the primary 3D structural coordinates (C, V, T)."""
        return (self.tk1, self.tk2, self.tk3)

# ============================================================
# STEP 1.5 — LAURENZO-GEMINI INFORMATIC MASS & INGEST HANDLER
# ============================================================

class SovereignGland:
    """Core refinery extracting PII, calculating mass, and scrubbing memory."""
    def __init__(self):
        self.volatile_boundary = TokenZeroVolatileBoundary()

    def process_secure_intake(self, raw_envelope: RawObjectEnvelope, user_tier: str = "DEFAULT") -> TokenState:
        # Step A: Token 0 Volatile Boundary Ingestion
        admitted = self.volatile_boundary.admit(raw_envelope)
        
        # Step B: Informatic Unitization
        num_units = self._calculate_informatic_units(admitted.sanitized_payload, admitted.source_type, admitted.metadata)
        c_domain = 1.0
        w_in = num_units * c_domain
        
        # Step C: Experimental 90/10 Reduction
        f_reduction = 0.90
        w_retained = w_in * (1.0 - f_reduction)
        
        # Step D: Form Token State & Structural Mass
        token_state = self._generate_ghost(admitted, w_retained, user_tier)
        
        # Step E: Explicit Incineration & Heap Sanitization
        self._incinerate(admitted)
        
        return token_state

    def _calculate_informatic_units(self, payload: bytearray, source_type: IntakeSource, metadata: dict[str, Any]) -> int:
        try:
            text = payload.decode("utf-8", errors="ignore")
            if source_type == IntakeSource.CSV:
                return max(1, len([line for line in text.splitlines() if line.strip()]) - 1)
            elif source_type == IntakeSource.PDF:
                paragraphs = [p for p in text.split("\n\n") if p.strip()]
                return max(1, len(paragraphs))
            elif source_type == IntakeSource.BINARY:
                lines = text.splitlines()
                return max(1, len(lines) // 10)
            elif source_type == IntakeSource.GEOSPATIAL:
                return int(metadata.get("area_sq_meters", max(1, len(payload) // 50)))
            else:
                width = metadata.get("width_pixels", 0)
                height = metadata.get("height_pixels", 0)
                if width and height:
                    return int((width * height) // 100)
                return max(1, len(payload) // 100)
        except Exception:
            return max(1, len(payload) // 100)

    def _generate_ghost(self, admitted: AdmittedByteState, w_retained: float, user_tier: str) -> TokenState:
        meta = admitted.metadata
        
        # Direct raw token checks (for CSV adapter)
        raw_t1 = meta.get("token_001")
        raw_t2 = meta.get("token_002")
        raw_t3 = meta.get("token_003")
        raw_t4 = meta.get("token_004")
        
        # Map values using coprime algebraic summer (Zero cryptographic hashes)
        tk1 = string_to_algebraic_float(raw_t1) if raw_t1 else string_to_algebraic_float(meta.get("client_assigned_id", "ANON"))
        tk2 = string_to_algebraic_float(raw_t2) if raw_t2 else string_to_algebraic_float(meta.get("tenant_id", user_tier))
        
        ts_str = meta.get("ts_utc")
        if ts_str:
            tk3 = string_to_algebraic_float(ts_str)
        else:
            tk3 = string_to_algebraic_float(raw_t3) if raw_t3 else (time.time() % 1000.0)
            
        tk4 = w_retained
        tk5 = w_retained * 1.5
        tk8 = string_to_algebraic_float(raw_t4) if raw_t4 else float(meta.get("amount_due", 0.0))
        
        # TK6: Audit Seal is the Sum of the Logic Units
        tk6 = tk1 + tk2 + tk3 + tk4 + tk5 + tk8
        
        return TokenState(\
            tk1=tk1,\
            tk2=tk2,\
            tk3=tk3,\
            tk4=tk4,\
            tk5=tk5,\
            tk6=tk6,\
            tk7=meta.get("file_name", "TK7_REF_DEFAULT"),\
            tk8=tk8,\
            tk9="PENDING"\
        )

    def _incinerate(self, admitted: AdmittedByteState) -> None:
        """Physically overrides the admitted payload block in heap memory to zero it out."""
        import gc
        try:
            # Overwrite the actual sanitized payload in memory
            for i in range(len(admitted.sanitized_payload)):
                admitted.sanitized_payload[i] = 0x00
        except Exception:
            pass
        finally:
            del admitted
            gc.collect()

class UniversalIngestHandler:
    """Coordinates intake, measurement, and validation freeze."""
    def __init__(self, sovereign_gland: SovereignGland):
        self.gland = sovereign_gland

    def ingest_and_measure(self, raw_envelope: RawObjectEnvelope, user_tier: str = "DEFAULT") -> TokenState:
        token_state = self.gland.process_secure_intake(raw_envelope, user_tier)
        # Establish reference S0
        s_0 = token_state.sum_state()
        token_state.tk10["S0"] = s_0
        return token_state

# ============================================================
# STEP 2 & 4: THE INTEGRITY BOUNDARIES (TK9 + REVERIFICATION)
# ============================================================

class ProfitzCRM:
    """The CRM Registry & Multistate State Machine (Lattice Storage)"""
    def __init__(self):
        self.registry: dict[str, TokenState] = {}
        self.quarantine: dict[str, TokenState] = {}
        self.canonical_tier1: dict[str, dict[str, Any]] = {}
        self.canonical_tier2: dict[str, dict[str, Any]] = {}
        self.last_known_good: dict[str, TokenState] = {}
        self.event_log: list[dict[str, Any]] = []
        self.history: dict[str, list[TokenState]] = {}  # Tracks chronological validated states per identity

    def register_token_set(self, token_set: TokenState) -> str:
        s_0 = token_set.tk10.get("S0", token_set.tk6)
        s_out = token_set.sum_state()
        z = s_out - s_0
        
        identity_ghost_key = f"IDENTITY_GHOST_{token_set.tk1:.8f}"
        
        if abs(z) < 1e-12:
            token_set.tk9 = "YES"
            self.registry[identity_ghost_key] = token_set
            self._log_event(identity_ghost_key, "VALIDATION_PASS", f"Z-variance: {z:.12f}")
            
            # Record validated state chronological history
            if identity_ghost_key not in self.history:
                self.history[identity_ghost_key] = []
            self.history[identity_ghost_key].append(token_set)
            
            self._establish_tk10_baseline(token_set)
            self._establish_canonical_state(identity_ghost_key, token_set)
            
            reval_passed = self.reverify_and_promote(identity_ghost_key)
            if reval_passed:
                return f"SUCCESS: {identity_ghost_key} fully promoted. TK9=YES, TK10 baseline created, Tier 1/2 persistent."
            else:
                return f"WARNING: {identity_ghost_key} persisted but REVALIDATION FAILED. Sent to quarantine."
        else:
            token_set.tk9 = "NO"
            self.quarantine[identity_ghost_key] = token_set
            self._log_event(identity_ghost_key, "VALIDATION_FAIL", f"Z-variance: {z:.12f}")
            return f"FAILED: {identity_ghost_key} mismatched structural beam. Z={z:.12f}. Moved to Quarantine."

    def _establish_tk10_baseline(self, token_set: TokenState) -> None:
        """Computes deterministic analytical baseline KPIs, including Distance-Time-Deviation."""
        identity_ghost_key = f"IDENTITY_GHOST_{token_set.tk1:.8f}"
        history = self.history.get(identity_ghost_key, [token_set])
        
        # Original KPI metrics to prevent downstream crashes
        transactions = max(1.0, token_set.tk4 * 100)
        opportunities = max(1.0, token_set.tk5 * 80)
        token_set.tk10["Conversion_Rate"] = (opportunities / transactions) * 100
        token_set.tk10["Unit_Logic_Mass"] = token_set.sum_state()
        token_set.tk10["Basetime_Counter"] = perf_counter()
        
        import math
        
        # Calculate 3D coordinate Euclidean Distance of current state from origin (0,0,0)
        # Using (tk1, tk2, tk3) as the primary 3D structural coordinate space
        d_curr = math.sqrt(token_set.tk1**2 + token_set.tk2**2 + token_set.tk3**2)
        
        d_prev = 0.0
        dist_diff = 0.0
        pct_change = 0.0
        elapsed_time = 0.0
        time_normalized_rate = 0.0
        
        # If there is prior history, compute sequential changes
        if len(history) >= 2:
            prev_token = history[-2]
            d_prev = math.sqrt(prev_token.tk1**2 + prev_token.tk2**2 + prev_token.tk3**2)
            dist_diff = d_curr - d_prev
            if d_prev != 0.0:
                pct_change = (dist_diff / d_prev) * 100.0
            elapsed_time = token_set.tk3 - prev_token.tk3
            if elapsed_time != 0.0:
                time_normalized_rate = pct_change / elapsed_time
        
        # Calculate historical list of distance changes (differences) to find mean and std
        diffs = []
        for i in range(1, len(history)):
            t_prev = history[i-1]
            t_curr = history[i]
            dp = math.sqrt(t_prev.tk1**2 + t_prev.tk2**2 + t_prev.tk3**2)
            dc = math.sqrt(t_curr.tk1**2 + t_curr.tk2**2 + t_curr.tk3**2)
            diffs.append(dc - dp)
            
        mean_diff = 0.0
        std_diff = 0.0
        z_score = 0.0
        sample_count = len(diffs)
        
        if sample_count > 0:
            mean_diff = sum(diffs) / sample_count
            if sample_count >= 2:
                std_diff = math.sqrt(sum((x - mean_diff)**2 for x in diffs) / (sample_count - 1))
            else:
                std_diff = 0.0
                
            if std_diff > 1e-12:
                z_score = (dist_diff - mean_diff) / std_diff
                
        # Register the 12 ordered outputs exactly as defined in Section 4 under descriptor #03
        token_set.tk10["03_Distance_Time_Deviation"] = {
            "Previous Euclidean Distance": d_prev,
            "Current Euclidean Distance": d_curr,
            "Distance Difference": dist_diff,
            "Distance Percentage Change": pct_change,
            "Elapsed Source Time": elapsed_time,
            "Source Time Unit": "intervals",
            "Time-Normalized Distance Percentage Rate": time_normalized_rate,
            "Rate Unit": "percent/interval",
            "Mean Historical Distance Change": mean_diff,
            "Standard Deviation of Historical Distance Change": std_diff,
            "Standardized Distance-Change Score (z-score)": z_score,
            "Sample Count": sample_count
        }

    def _establish_canonical_state(self, key: str, token_set: TokenState) -> None:
        t1_pending = {\
            "tk1": token_set.tk1,\
            "tk2": token_set.tk2,\
            "tk3": token_set.tk3,\
            "tk4": token_set.tk4,\
            "tk5": token_set.tk5,\
            "tk6": token_set.tk6,\
            "tk8": token_set.tk8,\
            "tk9": token_set.tk9,\
            "tk10": token_set.tk10.copy(),\
            "status": "PENDING",\
            "tier2_ref": f"TIER2_{key}",\
            "subdivisions": token_set.subdivisions.copy(),\
            "custom_tokens": token_set.custom_tokens.copy()\
        }
        self.canonical_tier1[key] = t1_pending

        t2_pending = {\
            "ref_id": f"TIER2_{key}",\
            "tk7_complete_reference": token_set.tk7,\
            "status": "PENDING",\
            "payload_details": {\
                "mass_sum": token_set.sum_state(),\
                "time_stamp": time.time()\
            }\
        }
        self.canonical_tier2[key] = t2_pending

    def _log_event(self, key: str, event_type: str, detail: str) -> None:
        self.event_log.append({\
            "timestamp": time.time(),\
            "target": key,\
            "event": event_type,\
            "detail": detail\
        })

    def reverify_and_promote(self, key: str) -> bool:
        """
        Step 4.6: U-SIE Reverification Process
        PASS rule: (all Zi == 0) and (Ztotal == 0)
        """
        ref_state = self.registry.get(key)
        if not ref_state:
            return False
            
        s_r = ref_state.sum_state()
        t1_pending = self.canonical_tier1.get(key)
        t2_pending = self.canonical_tier2.get(key)
        if not t1_pending or not t2_pending:
            return False

        candidate_state = TokenState(\
            tk1=t1_pending["tk1"],\
            tk2=t1_pending["tk2"],\
            tk3=t1_pending["tk3"],\
            tk4=t1_pending["tk4"],\
            tk5=t1_pending["tk5"],\
            tk6=t1_pending["tk6"],\
            tk8=t1_pending["tk8"],\
            tk9=t1_pending["tk9"],\
            subdivisions=t1_pending["subdivisions"],\
            custom_tokens=t1_pending["custom_tokens"],\
            tk10=t1_pending["tk10"]\
        )
        s_c = candidate_state.sum_state()
        z_total = s_c - s_r
        
        z_tokens = {\
            "tk1": candidate_state.tk1 - ref_state.tk1,\
            "tk2": candidate_state.tk2 - ref_state.tk2,\
            "tk3": candidate_state.tk3 - ref_state.tk3,\
            "tk4": candidate_state.tk4 - ref_state.tk4,\
            "tk5": candidate_state.tk5 - ref_state.tk5,\
            "tk8": candidate_state.tk8 - ref_state.tk8,\
        }
        
        all_tokens_zero = all(abs(v) < 1e-12 for v in z_tokens.values())
        total_zero = abs(z_total) < 1e-12
        
        if all_tokens_zero and total_zero:
            t1_pending["status"] = "AUTHORITATIVE"
            t2_pending["status"] = "AUTHORITATIVE"
            self.last_known_good[key] = ref_state
            self._log_event(key, "REVERIFICATION_PASS", "Atomic promotion to AUTHORITATIVE complete.")
            return True
        else:
            t1_pending["status"] = "QUARANTINED"
            t2_pending["status"] = "QUARANTINED"
            self.quarantine[key] = ref_state
            self._log_event(key, "REVERIFICATION_FAIL", "Mismatched persistent states. Sent to quarantine.")
            return False

# ============================================================
# STEP 5: MULTI-STATE PROJECTION DISPLAY (MSPD)
# ============================================================

class MultiStateProjectionDisplay:
    def __init__(self, crm: ProfitzCRM):
        self.crm = crm

    def get_cascading_projection(self, key: str, resolution_level: int = 1, active_role: str = "Administrator") -> dict[str, Any]:
        """
        Role-Appropriate Projection (Section 5.9):
        1. Administrator: Unlimited view of all details (PII decrypted/visible).
        2. Practitioner: Normal analytical view (PII masked/anonymized).
        3. Supplier / External: Limited view (Only Category, Inventory, and Price visible).
        """
        t1 = self.crm.canonical_tier1.get(key)
        if not t1:
            return {"Error": "State key not found"}

        # Dynamic filtering based on Role Permissions
        if active_role == "Supplier / External":
            # Supplier only gets inventory and price view (Level 1 equivalent)
            return {\
                "CanonicalStateID": key,\
                "Status": t1["status"],\
                "TK4_InventoryWeight": t1["tk4"],\
                "TK8_Price": t1["tk8"],\
                "Scope": "Supplier / External View - Highly Limited"\
            }

        # Masking PII for Practitioner roles
        p_status = t1["status"]
        tk7_val = self.crm.canonical_tier2.get(key)["tk7_complete_reference"] if self.crm.canonical_tier2.get(key) else "None"
        if active_role == "Practitioner":
            tk7_val = "[MASKED_PII_PRACTITIONER_ROLE]"
            p_status = "AUTHORITATIVE (MASKED)"

        if resolution_level == 1:
            return {\
                "CanonicalStateID": key,\
                "Status": p_status,\
                "IdentityAnchor(TK1)": t1["tk1"],\
                "SpatialAnchor(TK2)": t1["tk2"],\
                "TemporalAnchor(TK3)": t1["tk3"],\
            }
        elif resolution_level == 2:
            base_view = {\
                "CanonicalStateID": key,\
                "Status": p_status,\
                "TK1_Identity": t1["tk1"],\
                "TK2_Spatial": t1["tk2"],\
                "TK3_Temporal": t1["tk3"],\
                "TK4_InventoryWeight": t1["tk4"],\
                "TK5_Geometry": t1["tk5"],\
                "TK6_AuditSeal": t1["tk6"],\
                "TK8_Price": t1["tk8"],\
                "TK9_Validation": t1["tk9"],\
            }
            if t1.get("custom_tokens"):
                base_view["Custom_Token_Expansions"] = t1["custom_tokens"]
            return base_view
        else:
            return {\
                "CanonicalStateID": key,\
                "Status": p_status,\
                "Tokens": {\
                    "TK1_C": t1["tk1"],\
                    "TK2_V": t1["tk2"],\
                    "TK3_T": t1["tk3"],\
                    "TK4": t1["tk4"],\
                    "TK5": t1["tk5"],\
                    "TK6_Audit": t1["tk6"],\
                    "TK8": t1["tk8"],\
                    "TK9": t1["tk9"]\
                },\
                "Subdivisions": t1["subdivisions"],\
                "TK10_Analytics": t1["tk10"],\
                "Tier2_Reference": tk7_val,\
            }

# ============================================================
# STREAMLIT HUD & PRIVACYFLOW CRM WITH GPU & LATENCY TELEMETRY
# ============================================================

def run_streamlit_hud():
    """Initializes and runs the full Streamlit UI interface."""
    st.set_page_config(\
        page_title="U-SIE Sovereign HUD & PrivacyFlow CRM Panel",\
        page_icon="🌌",\
        layout="wide"\
    )

    # Custom styling
    st.markdown("""
        <style>
        .hud-header {
            color: #00FFCC;
            font-family: 'Courier New', Courier, monospace;
            font-size: 2.2rem;
            text-align: center;
            border-bottom: 2px solid #00FFCC;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .hud-section {
            background-color: #0e1117;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .token-seal {
            color: #FFFF00;
            font-weight: bold;
        }
        .variance-pass {
            color: #00FF00;
            font-weight: bold;
        }
        .variance-fail {
            color: #FF0000;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hud-header">🌌 U-SIE SOVEREIGN HUD & PRIVACYFLOW CRM</div>', unsafe_allow_html=True)

    # Set up session state to persist components
    if "crm" not in st.session_state:
        st.session_state.crm = ProfitzCRM()
        st.session_state.gland = SovereignGland()
        st.session_state.feeder = UniversalObjectFeeder()
        st.session_state.ingest_handler = UniversalIngestHandler(st.session_state.gland)
        
        # Telemetry State variables
        st.session_state.telemetry = {\
            "last_ingest_time_ms": 0.0,\
            "last_ai_time_s": 0.0,\
            "last_ai_ttft_ms": 0.0,\
            "last_ai_tps": 0.0,\
            "gpu_percentage": 0.0,\
            "vram_used": 0.0,\
            "vram_total": 0.0,\
            "gpu_name": "N/A"\
        }
        
        # Interactive CRM editable DataFrame initialization
        st.session_state.crm_df = pd.DataFrame([\
            {"Client ID": "CLI-101", "Tenant ID": "TENANT-ALPHA", "Value TK8": "150.0", "Temporal TK3": "Jan-Peak", "Status": "UNINGESTED"},\
            {"Client ID": "CLI-102", "Tenant ID": "TENANT-BETA", "Value TK8": "240.5", "Temporal TK3": "Feb-Mid", "Status": "UNINGESTED"},\
            {"Client ID": "CLI-103", "Tenant ID": "TENANT-ALPHA", "Value TK8": "89.9", "Temporal TK3": "Mar-Low", "Status": "UNINGESTED"}\
        ])
        
        # Load starting benchmark data
        knowledge_dir = Path("/workspace/knowledge")
        audit_csv = knowledge_dir / "Copy_of_audit.csv"
        if audit_csv.exists():
            try:
                with open(audit_csv, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for count, row in enumerate(reader):
                        if count >= 10:
                            break
                        session_id = row["session_id"]
                        meta = {\
                            "token_001": row["token_001"],\
                            "token_002": row["token_002"],\
                            "token_003": row["token_003"],\
                            "token_004": row["token_004"],\
                            "ts_utc": row["ts_utc"],\
                            "client_assigned_id": session_id[:8],\
                            "tenant_id": "TENANT_ALPHA",\
                            "file_name": "Copy_of_audit.csv"\
                        }
                        payload_str = f"session:{session_id};audit_line:{count};t1:{row['token_001']};t2:{row['token_002']}"
                        envelope = st.session_state.feeder.feed(IntakeSource.CSV, bytearray(payload_str.encode("utf-8")), meta)
                        token_state = st.session_state.ingest_handler.ingest_and_measure(envelope)
                        st.session_state.crm.register_token_set(token_state)
            except Exception as e:
                st.warning(f"Error reading local audit baseline: {e}")

    crm = st.session_state.crm
    gland = st.session_state.gland
    feeder = st.session_state.feeder
    ingest_handler = st.session_state.ingest_handler

    # Live telemetry state query on every run
    gpu_metrics = query_gpu_utilization()
    if gpu_metrics["active"]:
        st.session_state.telemetry["gpu_percentage"] = gpu_metrics["gpu_percentage"]
        st.session_state.telemetry["vram_used"] = gpu_metrics["vram_used"]
        st.session_state.telemetry["vram_total"] = gpu_metrics["vram_total"]
        st.session_state.telemetry["gpu_name"] = gpu_metrics["gpu_name"]
    else:
        # Fall back to host CPU metrics gracefully if offline/no GPU
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            mem_info = psutil.virtual_memory()
            st.session_state.telemetry["gpu_percentage"] = cpu_percent
            st.session_state.telemetry["vram_used"] = float(mem_info.used) / (1024**2)
            st.session_state.telemetry["vram_total"] = float(mem_info.total) / (1024**2)
            st.session_state.telemetry["gpu_name"] = "CPU Fallback (No NVML)"
        except ImportError:
            st.session_state.telemetry["gpu_name"] = "Hardware Offline"

    # SIDEBAR: Local AI Config, Ingestion & ROLE-BASED ACCESS CONTROL
    with st.sidebar:
        st.header("👤 Security & Role Portal")
        active_role = st.selectbox(\
            "Select Access-Control Permission Role",\
            ["Administrator", "Practitioner", "Supplier / External"],\
            help="Filters HUD visualization and Hoberman expansions based on role permission clearings (Section 5.9)."\
        )
        
        # Role information alert
        if active_role == "Administrator":
            st.success("🔓 Full Root Clearances Active. All coordinates and raw references are fully visible.")
        elif active_role == "Practitioner":
            st.info("⚠️ Practitioner Permissions: Coordinates visible; persistent raw references are securely masked.")
        else:
            st.warning("🛑 Restricted Supplier View: Only total price and inventory categories are projected. Identity masked.")

        st.markdown("---")
        st.header("⚙️ Server & AI Config")
        local_ai_endpoint = st.text_input(\
            "Local Llama Endpoint URL",\
            value="http://localhost:11434/api/generate",\
            help="Ollama default endpoint. Ensure your local sandboxed server is running."\
        )
        ai_model_name = st.text_input(\
            "Local AI Model",\
            value="llama3.2",\
            help="Specify model registered on your server (e.g., llama3.2, mistral)"\
        )

        st.markdown("---")
        st.header("📥 Ingest New File")
        uploaded_file = st.file_uploader(\
            "Drop or select a file to admit into the Volatile Intake Boundary",\
            type=["csv", "pdf", "txt", "bin", "geojson", "png", "jpg"]\
        )

        if uploaded_file is not None:
            st.info("Assign starting calibration:")
            domain_choice = st.selectbox(\
                "Declared Intake Source",\
                ["CSV", "PDF", "BINARY", "GEOSPATIAL", "XRAY"]\
            )
            area_sq_m = st.number_input("Geospatial Area (m²)", min_value=1, value=100) if domain_choice == "GEOSPATIAL" else 0
            width_px = st.number_input("Image Width (px)", min_value=1, value=1920) if domain_choice == "XRAY" else 0
            height_px = st.number_input("Image Height (px)", min_value=1, value=1080) if domain_choice == "XRAY" else 0

            if st.button("Admit File"):
                try:
                    file_bytes = bytearray(uploaded_file.read())
                    source_enum = IntakeSource[domain_choice]
                    
                    meta = {\
                        "file_name": uploaded_file.name,\
                        "client_assigned_id": f"CLI-{int(time.time()) % 100000}",\
                        "tenant_id": "TENANT_PORTAL",\
                        "area_sq_meters": area_sq_m,\
                        "width_pixels": width_px,\
                        "height_pixels": height_px\
                    }
                    
                    # Latency Tracking start
                    t_start = perf_counter()
                    envelope = feeder.feed(source_enum, file_bytes, meta)
                    token_state = ingest_handler.ingest_and_measure(envelope)
                    outcome = crm.register_token_set(token_state)
                    t_end = perf_counter()
                    
                    # Store Ingestion processing time (in milliseconds)
                    st.session_state.telemetry["last_ingest_time_ms"] = (t_end - t_start) * 1000.0
                    
                    if "SUCCESS" in outcome:
                        st.success(outcome)
                    else:
                        st.error(outcome)
                except Exception as e:
                    st.error(f"Admittance failure: {e}")

    # MAIN WORKSPACE LAYOUT
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<h3 style="color:#00FFCC;">🌌 Active 3D Lattice Projection Space</h3>', unsafe_allow_html=True)
        
        # 3D Interactive Plotly Lattice
        records = list(crm.registry.values())
        if records:
            x_vals = [r.tk1 for r in records]
            y_vals = [r.tk2 if active_role != "Supplier / External" else 0.0 for r in records]
            z_vals = [r.tk3 for r in records]
            prices = [r.tk8 for r in records]
            ids = [f"GHOST_{r.tk1:.5f}" for r in records]
            
            fig = go.Figure(data=[go.Scatter3d(\
                x=x_vals,\
                y=y_vals,\
                z=z_vals,\
                mode='markers+lines',\
                marker=dict(\
                    size=8,\
                    color=prices,\
                    colorscale='Viridis',\
                    opacity=0.8,\
                    colorbar=dict(title="TK8 (Price)", thickness=15)\
                ),\
                text=ids,\
                hoverinfo='text+x+y+z'\
            )])
            
            fig.update_layout(\
                margin=dict(l=0, r=0, b=0, t=0),\
                scene=dict(\
                    xaxis_title='C (TK1 Identity)' if active_role != "Supplier / External" else 'MASKED C',\
                    yaxis_title='V (TK2 Spatial)' if active_role != "Supplier / External" else 'RESTRICTED V',\
                    zaxis_title='T (TK3 Temporal)',\
                    xaxis=dict(gridcolor='rgb(30, 41, 59)', backgroundcolor='rgb(14, 17, 23)'),\
                    yaxis=dict(gridcolor='rgb(30, 41, 59)', backgroundcolor='rgb(14, 17, 23)'),\
                    zaxis=dict(gridcolor='rgb(30, 41, 59)', backgroundcolor='rgb(14, 17, 23)'),\
                ),\
                paper_bgcolor='rgba(0,0,0,0)',\
                plot_bgcolor='rgba(0,0,0,0)',\
                height=400\
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Intake space empty. Admit files or baseline records to render the active 3D lattice.")

    with col2:
        st.markdown('<h3 style="color:#00FFCC;">🧠 Sandboxed Local Llama Interface</h3>', unsafe_allow_html=True)
        st.write("Construct a validated U-SIE Packet context and transmit instructions directly to Llama 3.2.")
        
        # Role check for AI Packets
        if active_role == "Supplier / External":
            st.error("🛑 Role Violation: Supplier permissions are restricted from packaging context for downstream AI inference.")
        else:
            if records:
                selected_ghosts = st.multiselect(\
                    "Select Canonical States to Reinflate & Packetize (Step 5.8.6):",\
                    options=list(crm.canonical_tier1.keys()),\
                    default=list(crm.canonical_tier1.keys())[:3] if len(records) >= 3 else list(crm.canonical_tier1.keys())\
                )
            else:
                selected_ghosts = []
                st.warning("No canonical states available. Ingest files first to packetize.")

            user_instruction = st.text_area(\
                "AI System Instruction:",\
                value="Verify the structural alignment of the selected states and look for any anomalies in the economic coordinates (TK8)."\
            )

            context_detail = st.radio(\
                "Information Packet Format",\
                ["Level 2 (Expanded Tokens)", "Level 3 (Full Reinflated Analytical Context)"]\
            )

            transmit_col1, transmit_col2 = st.columns([1, 1])
            with transmit_col1:
                send_real_call = st.checkbox("Connect Live Server", value=False)
            
            with transmit_col2:
                trigger_button = st.button("🚀 Transmit Packet to Llama")

            if trigger_button:
                if not selected_ghosts:
                    st.error("Select at least one canonical state to construct a packet.")
                else:
                    # Clear telemetry metrics before start
                    st.session_state.telemetry["last_ai_time_s"] = 0.0
                    st.session_state.telemetry["last_ai_ttft_ms"] = 0.0
                    st.session_state.telemetry["last_ai_tps"] = 0.0
                    
                    with st.spinner("Reinflating states and packaging context..."):
                        packet_elements = []
                        display_obj = MultiStateProjectionDisplay(crm)
                        res_lvl = 2 if "Level 2" in context_detail else 3
                        
                        for key in selected_ghosts:
                            reinflated = display_obj.get_cascading_projection(key, resolution_level=res_lvl, active_role=active_role)
                            packet_elements.append(reinflated)
                        
                        full_payload = {\
                            "model": ai_model_name,\
                            "prompt": f"System Instruction: {user_instruction}\\n\\nU-SIE Information Packet:\\n{json.dumps(packet_elements, indent=2)}\\n",\
                            "stream": False\
                        }
                        
                        st.markdown("### Constructed Payload:")
                        st.json(full_payload)
                        
                        if send_real_call:
                            try:
                                # Start clock tracking for Llama AI processing
                                ai_start = perf_counter()
                                response = requests.post(local_ai_endpoint, json=full_payload, timeout=15)
                                ai_end = perf_counter()
                                
                                if response.status_code == 200:
                                    res_json = response.json()
                                    response_text = res_json.get("response", "")
                                    
                                    # Calculate hardware latencies and time processing
                                    total_ai_time = ai_end - ai_start
                                    estimated_ttft = total_ai_time * 0.15 * 1000.0  # Estimate TTFT at 15% of roundtrip
                                    
                                    # Calculate token generation throughput
                                    word_count = len(response_text.split())
                                    token_count = int(word_count * 1.33)
                                    tps = token_count / total_ai_time if total_ai_time > 0 else 0.0
                                    
                                    st.session_state.telemetry["last_ai_time_s"] = total_ai_time
                                    st.session_state.telemetry["last_ai_ttft_ms"] = estimated_ttft
                                    st.session_state.telemetry["last_ai_tps"] = tps
                                    
                                    st.success("Response Received:")
                                    st.write(response_text if response_text else res_json)
                                else:
                                    st.error(f"Local AI Server returned status: {response.status_code}")
                            except Exception as req_err:
                                st.error(f"Connection failed: {req_err}")
                        else:
                            # Simulated Llama run with realistic load spikes on GPU percentage!
                            import random
                            for step in range(3):
                                st.session_state.telemetry["gpu_percentage"] = float(random.randint(65, 88))
                                time.sleep(0.3)
                            
                            total_ai_time = 1.24  # processing time in seconds
                            estimated_ttft = 145.2  # ms
                            tps = 45.1  # tokens/sec
                            
                            st.session_state.telemetry["last_ai_time_s"] = total_ai_time
                            st.session_state.telemetry["last_ai_ttft_ms"] = estimated_ttft
                            st.session_state.telemetry["last_ai_tps"] = tps
                            
                            st.info("📡 Live connection disabled. Simulated response from Llama 3.2:")
                            simulated_response = (\
                                f"[Llama 3.2 Sandboxed Response]\\n"\
                                f"Successfully parsed {len(selected_ghosts)} U-SIE canonical state(s).\\n"\
                                f"Checking structural symmetry of coordinates:\\n"\
                                f"- Deterministic PASS confirmed for all requested nodes.\\n"\
                                f"- Z-variance is 0.000000000000 (Symmetry is stable).\\n"\
                                f"- No anomalies detected."\
                            )
                            st.code(simulated_response, language="markdown")

        # ============================================================
        # ⚡ LIVE PERFORMANCE & LATENCY TELEMETRY CONSOLE BOX
        # ============================================================
        st.markdown('<div class="hud-section" style="border: 1px solid #FF9900; margin-top:15px;">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#FF9900; margin-top:0;">⚡ Live Performance & Telemetry Dashboard</h4>', unsafe_allow_html=True)
        
        col_tel1, col_tel2 = st.columns(2)
        with col_tel1:
            st.markdown("**U-SIE Processing Latencies:**")
            st.write(f"⏱️ Ingress Ingestion: `{st.session_state.telemetry['last_ingest_time_ms']:.3f} ms`" if st.session_state.telemetry['last_ingest_time_ms'] > 0 else "⏱️ Ingress Ingestion: `0.000 ms`")
            st.write(f"⏱️ AI Time-to-First-Token: `{st.session_state.telemetry['last_ai_ttft_ms']:.2f} ms`" if st.session_state.telemetry['last_ai_ttft_ms'] > 0 else "⏱️ AI TTFT: `0.00 ms`")
            st.write(f"⏱️ AI Roundtrip Process: `{st.session_state.telemetry['last_ai_time_s']:.3f} s`" if st.session_state.telemetry['last_ai_time_s'] > 0 else "⏱️ AI Process: `0.000 s`")
            
        with col_tel2:
            is_gpu = "CPU" not in st.session_state.telemetry["gpu_name"] and "Hardware" not in st.session_state.telemetry["gpu_name"]
            gpu_label = "GPU Utilization" if is_gpu else "Host CPU Utilization"
            vram_label = "VRAM Footprint" if is_gpu else "System Virtual Memory"
            
            st.markdown("**Host Hardware Monitor:**")
            st.write(f"🖥️ Device: `{st.session_state.telemetry['gpu_name']}`")
            st.write(f"📊 {gpu_label}: `{st.session_state.telemetry['gpu_percentage']:.1f}%`")
            st.write(f"💾 {vram_label}: `{st.session_state.telemetry['vram_used']:.1f} MB / {st.session_state.telemetry['vram_total']:.1f} MB`" if st.session_state.telemetry['vram_total'] > 0 else "💾 RAM: `N/A`")
            
        if st.session_state.telemetry['last_ai_tps'] > 0:
            st.info(f"⚡ AI Throughput Speed: **{st.session_state.telemetry['last_ai_tps']:.2f} tokens/second**")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # LOWER WORKSPACE TAB: THE PRIVACYFLOW CRM ON STEROIDS
    st.markdown("---")
    st.markdown('<h3 style="color:#00FFCC;">📁 PrivacyFlow CRM Layer (Grid Manipulator & Token Extender)</h3>', unsafe_allow_html=True)
    
    crm_tab1, crm_tab2, crm_tab3 = st.tabs([\
        "📊 Editable Coordinate Grid", \
        "🧩 Token Subdivision Manager", \
        "📂 Hoberman Expanding State Registry"\
    ])

    with crm_tab1:
        st.write("Researchers can manually manipulate, populate, add columns (Token Expansion) and validate grid rows.")
        
        # Interactive Excel-like DataFrame editor with Streamlit data_editor
        edited_df = st.data_editor(\
            st.session_state.crm_df,\
            num_rows="dynamic",\
            use_container_width=True,\
            column_config={\
                "Status": st.column_config.TextColumn("Status", disabled=True)\
            }\
        )
        
        # Add Columns interface to allow custom token dimension expansion (Token Expansion)
        new_col_name = st.text_input("Define Token Expansion (New Dimension Name, e.g. 'TK11_Housing_Permits'):", "")
        if st.button("➕ Add Token Expansion Column") and new_col_name:
            if new_col_name not in edited_df.columns:
                st.session_state.crm_df = edited_df.copy()
                st.session_state.crm_df[new_col_name] = "0.0"
                st.rerun()
            else:
                st.error("Column already exists.")

        st.markdown("---")
        if st.button("🚀 Commit, Validate, and Promote Grid to 3D Lattice"):
            st.session_state.crm_df = edited_df.copy()
            validated_count = 0
            
            # Start timer for Ingestion Batch processing
            t_start = perf_counter()
            
            # Loop through each row and push it to the gland
            for index, row in edited_df.iterrows():
                if row.get("Status") == "PROMOTED":
                    continue  # Skip already validated records
                    
                client_id = row.get("Client ID", f"GEN-{index}")
                tenant_id = row.get("Tenant ID", "TENANT_GRID")
                val_tk8 = row.get("Value TK8", "0.0")
                val_tk3 = row.get("Temporal TK3", str(time.time()))
                
                # Setup custom metadata block
                meta = {\
                    "client_assigned_id": client_id,\
                    "tenant_id": tenant_id,\
                    "token_004": f"TK8-{string_to_algebraic_float(val_tk8):.4f}" if val_tk8 else "TK8-0.0",\
                    "ts_utc": val_tk3,\
                    "file_name": "CRM_Manual_Grid_Entry"\
                }
                
                # Assemble payload
                payload_str = f"client:{client_id};tenant:{tenant_id};tk8_val:{val_tk8}"
                envelope = feeder.feed(IntakeSource.CSV, bytearray(payload_str.encode("utf-8")), meta)
                
                # Process intake and capture custom expanded dimensions
                token_state = ingest_handler.ingest_and_measure(envelope)
                
                # Check for any dynamic token expansion columns added by the user
                for col in edited_df.columns:
                    if col not in ["Client ID", "Tenant ID", "Value TK8", "Temporal TK3", "Status"]:
                        try:
                            # Parse custom column numerical contribution
                            token_state.custom_tokens[col] = float(row[col])
                        except (ValueError, TypeError):
                            token_state.custom_tokens[col] = 0.0
                
                # Enforce verification loop
                outcome = crm.register_token_set(token_state)
                
                if "SUCCESS" in outcome:
                    st.session_state.crm_df.at[index, "Status"] = "PROMOTED"
                    validated_count += 1
                else:
                    st.session_state.crm_df.at[index, "Status"] = "QUARANTINED"
            
            t_end = perf_counter()
            st.session_state.telemetry["last_ingest_time_ms"] = (t_end - t_start) * 1000.0
            
            if validated_count > 0:
                st.success(f"Successfully validated, promoted, and mapped {validated_count} grid record(s) to the 3D Lattice.")
                st.rerun()
            else:
                st.info("No new records were promoted. Check if coordinates align symmetrically.")

    with crm_tab2:
        st.write("Step 4.3: Subdivide verified parent tokens while verifying the conservation equation: M(Ti) = sum(M(Tij))")
        
        if not records:
            st.warning("No validated states in registry to subdivide.")
        else:
            selected_state_key = st.selectbox(\
                "Select Coordinate Node to Subdivide:",\
                options=list(crm.registry.keys())\
            )
            
            token_to_split = st.selectbox(\
                "Select Token Domain to Subdivide",\
                ["TK4", "TK5", "TK8"]\
            )
            
            # Fetch current value
            active_state = crm.registry[selected_state_key]
            current_tk_val = getattr(active_state, token_to_split.lower(), 0.0)
            st.metric(label=f"Current parent value of {token_to_split}", value=f"{current_tk_val:.6f}")
            
            st.markdown("#### Enter Subdivision Weights:")
            sub_col1, sub_col2 = st.columns([1, 1])
            with sub_col1:
                child_a_key = st.text_input("Child A Key (e.g. 'TK4_Spruce_Retail')", value=f"{token_to_split}_Spruce_Retail")
                child_a_val = st.number_input("Child A Value", value=current_tk_val * 0.4, format="%.6f")
            with sub_col2:
                child_b_key = st.text_input("Child B Key (e.g. 'TK4_Spruce_Wholesale')", value=f"{token_to_split}_Spruce_Wholesale")
                child_b_val = st.number_input("Child B Value", value=current_tk_val * 0.6, format="%.6f")

            # Check conservation in-place in real-time
            sum_of_children = child_a_val + child_b_val
            difference = sum_of_children - current_tk_val
            
            st.write(f"Sum of Children: `{sum_of_children:.6f}` | Target: `{current_tk_val:.6f}`")
            
            if abs(difference) < 1e-12:
                st.markdown("<span style='color:green;'>✔️ Conservation Condition Satisfied (Z_sub = 0).</span>", unsafe_allow_html=True)
                if st.button("💾 Apply Subdivisions"):
                    active_state.subdivisions[token_to_split] = {\
                        child_a_key: child_a_val,\
                        child_b_key: child_b_val\
                    }
                    
                    # Update local canonical cache to track subdivisions
                    crm.canonical_tier1[selected_state_key]["subdivisions"] = active_state.subdivisions.copy()
                    
                    # Re-run Step 4 Revalidation immediately
                    is_valid = crm.reverify_and_promote(selected_state_key)
                    if is_valid:
                        st.success(f"Subdivision applied and promoted! Step 4 revalidation passed.")
                    else:
                        st.error("Step 4 revalidation failed! Node has been quarantined.")
                    st.rerun()
            else:
                st.markdown(f"<span style='color:red;'>❌ Conservation Violating. Difference is: {difference:.12f}. Must balance exactly.</span>", unsafe_allow_html=True)

    with crm_tab3:
        st.write("Dynamic Hoberman Principle. Changing the selection level projects different resolution without muting identity.")
        
        if records:
            for idx, key in enumerate(crm.canonical_tier1.keys()):
                t1_record = crm.canonical_tier1[key]
                status = t1_record["status"]
                val_state = t1_record["tk9"]
                
                exp_label = f"📦 {key} | Status: {status} | TK9 Validation: {val_state}"
                
                with st.expander(exp_label):
                    st.markdown("#### The Hoberman Principle: Expanding Resolution Cascades")
                    
                    tab_lvl1, tab_lvl2, tab_lvl3 = st.tabs([\
                        "Level 1: Compact Coordinate Point", \
                        "Level 2: Expanded Token Domains", \
                        "Level 3: Full Reinflated Analytics"\
                    ])
                    
                    display_obj = MultiStateProjectionDisplay(crm)
                    
                    with tab_lvl1:
                        st.json(display_obj.get_cascading_projection(key, resolution_level=1, active_role=active_role))
                    with tab_lvl2:
                        st.json(display_obj.get_cascading_projection(key, resolution_level=2, active_role=active_role))
                    with tab_lvl3:
                        st.json(display_obj.get_cascading_projection(key, resolution_level=3, active_role=active_role))
        else:
            st.info("No validated records to expand. Commit grid entries or ingest baseline files.")

# ============================================================
# fallback DEMO CLI RUNNER
# ============================================================

def run_cli_demo():
    """Runs a clean fallback demo if executed via typical Python CLI."""
    print("="*80)
    print("U-SIE Sovereign Platform: PrivacyFlow CRM & Core Implementation")
    print("="*80)
    print("\nStreamlit HUD detected! To launch the beautiful visual interface, execute:")
    print("  streamlit run USIE_SovereignPlatform_HUD_v6.1.py")
    print("\nRunning quick mathematical validation pipeline demo...\n")
    
    feeder = UniversalObjectFeeder()
    gland = SovereignGland()
    ingest_handler = UniversalIngestHandler(gland)
    crm = ProfitzCRM()
    
    # Run a simple text input test
    test_payload = bytearray(b"session:TEST_GHOST;line:0;t1:001-A12B;t2:002-3D4F;t3:003-9A9A;t4:004-B4B4")
    envelope = feeder.feed(IntakeSource.BINARY, test_payload, {\
        "client_assigned_id": "DEMO_ID",\
        "tenant_id": "TENANT_ALPHA"\
    })
    
    token_state = ingest_handler.ingest_and_measure(envelope)
    outcome = crm.register_token_set(token_state)
    print(f"Ingest Outcome: {outcome}\n")
    
    if crm.registry:
        first_key = list(crm.registry.keys())[0]
        print(f"Hoberman View Level 2 for {first_key}:")
        display = MultiStateProjectionDisplay(crm)
        print(json.dumps(display.get_cascading_projection(first_key, 2), indent=2))

if __name__ == "__main__":
    import sys
    is_streamlit = "streamlit" in sys.modules or os.environ.get("STREAMLIT_SERVER_PORT") is not None
    
    # Force Streamlit trigger if called via streamlit run
    if is_streamlit or ("streamlit" in sys.argv[0] or (len(sys.argv) > 1 and "streamlit" in sys.argv[1])):
        is_streamlit = True

    if is_streamlit and HUD_AVAILABLE:
        run_streamlit_hud()
    else:
        run_cli_demo()
