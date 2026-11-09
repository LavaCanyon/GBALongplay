"""Deterministic byte-budget control for GLP video packets."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RateController:
    bytes_per_frame: float
    minimum_packet: int = 91
    burst_frames: float = 2.5
    repay_frames: float = 24.0
    floor_fraction: float = 0.40
    frame: int = 0
    actual_bytes: int = 0

    def budget(self) -> int:
        if self.bytes_per_frame <= 0: return self.minimum_packet
        error = self.actual_bytes - self.frame*self.bytes_per_frame
        floor = max(self.minimum_packet, self.bytes_per_frame*self.floor_fraction)
        cap = self.bytes_per_frame*self.burst_frames
        # Repay bursts gradually instead of starving several consecutive frames.
        # Credit is also spent gradually so packet sizes remain stable.
        proposed = self.bytes_per_frame - error/self.repay_frames
        return max(self.minimum_packet, int(min(cap, max(floor, proposed))))

    def commit(self, packet_bytes: int) -> None:
        self.actual_bytes += packet_bytes; self.frame += 1

    @property
    def target_bytes(self) -> float: return self.frame * self.bytes_per_frame

    @property
    def error_bytes(self) -> float: return self.actual_bytes - self.target_bytes


def video_budget(target_bytes: int, audio_bytes: int, frame_count: int,
                 index_and_header_bytes: int) -> float:
    remaining = target_bytes - audio_bytes - index_and_header_bytes
    if remaining <= 0: raise ValueError("target is too small for audio and indexes")
    return remaining / max(1, frame_count)
