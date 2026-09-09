# """
# block_logic.py — the punching-time -> block-number rule.

# Rule (parity-based, confirmed against real examples):
#     current_block = floor(minutes_since_midnight / 15) + 1        (1..96)

#     if current_block is ODD  -> punch blocks (current+6, current+7)
#     if current_block is EVEN -> punch blocks (current+7, current+8)

# Examples:
#     12:48 -> current block 52 (even) -> punch blocks 59, 60
#     13:17 -> current block 54 (even) -> punch blocks 61, 62 -> 15:00-15:15 / 15:15-15:30

# Blocks are numbered 1..96 across the day, block 1 = 00:00-00:15,
# block 96 = 23:45-00:00. If the +6/+7/+8 arithmetic pushes past 96, it rolls
# into the next calendar day's blocks (1, 2, 3, ...).
# """

# from dataclasses import dataclass
# from datetime import datetime, timedelta


# @dataclass
# class BlockWindow:
#     current_block: int
#     block1_num: int          # 1..96, day-local block number
#     block2_num: int          # 1..96, day-local block number
#     block1_start: datetime
#     block2_start: datetime
#     block2_end: datetime
#     block1_date_shift: bool  # True if block1 falls on a different calendar date than punch time
#     block2_date_shift: bool


# def current_block_number(dt: datetime) -> int:
#     """1-indexed block number within the day (1..96)."""
#     return (dt.hour * 60 + dt.minute) // 15 + 1


# def _block_to_datetime(raw_block_num: int, base_date):
#     """
#     raw_block_num can be > 96 (rolled into following day(s)).
#     Returns (start_dt, day_local_block_num, date_shifted: bool)
#     """
#     day_offset = (raw_block_num - 1) // 96
#     block_of_day = ((raw_block_num - 1) % 96) + 1
#     minutes_from_midnight = (block_of_day - 1) * 15
#     start_dt = datetime.combine(base_date, datetime.min.time()) + timedelta(
#         days=day_offset, minutes=minutes_from_midnight
#     )
#     return start_dt, block_of_day, day_offset > 0


# def compute_target_blocks(punch_time: datetime) -> BlockWindow:
#     current = current_block_number(punch_time)

#     if current % 2 == 1:  # odd
#         raw_b1, raw_b2 = current + 6, current + 7
#     else:  # even
#         raw_b1, raw_b2 = current + 7, current + 8

#     base_date = punch_time.date()
#     b1_start, b1_local, b1_shift = _block_to_datetime(raw_b1, base_date)
#     b2_start, b2_local, b2_shift = _block_to_datetime(raw_b2, base_date)
#     b2_end = b2_start + timedelta(minutes=15)

#     return BlockWindow(
#         current_block=current,
#         block1_num=b1_local,
#         block2_num=b2_local,
#         block1_start=b1_start,
#         block2_start=b2_start,
#         block2_end=b2_end,
#         block1_date_shift=b1_shift,
#         block2_date_shift=b2_shift,
#     )


# def format_range(bw: BlockWindow) -> str:
#     return f"{bw.block1_start:%H:%M}-{bw.block2_start:%H:%M} and {bw.block2_start:%H:%M}-{bw.block2_end:%H:%M}"


# GRACE_MINUTES = 15


# def compute_allowed_blocks(now: datetime, grace_minutes: int = GRACE_MINUTES):
#     """
#     Returns (current_window, min_editable_block, grace_window_or_none).

#     Protection model: only genuinely PAST blocks (whose punch time is over,
#     beyond the grace period) get locked to their previous baseline value.
#     Every block from the current punch window onward — including all future
#     blocks — stays freely editable, since forecasts for later blocks
#     legitimately change as the day goes on and shouldn't be locked in early.

#     `min_editable_block` is the cutoff: any block number >= this is editable
#     (current window, grace window if still in effect, and all future
#     blocks); any block number below it is treated as past and protected.

#     If you're a few minutes late — the window already shifted forward since
#     you finished punching on the actual government portal — blocks from the
#     previous window are still accepted for `grace_minutes` after the shift,
#     which is why the cutoff can be pulled back to the grace window's start
#     instead of the current window's start.

#     grace_window_or_none is the earlier BlockWindow if it's actually pulling
#     the cutoff back (i.e. a grace period is in effect right now), else None.
#     """
#     current_window = compute_target_blocks(now)
#     grace_window = compute_target_blocks(now - timedelta(minutes=grace_minutes))

#     current_blocks = {current_window.block1_num, current_window.block2_num}
#     grace_blocks = {grace_window.block1_num, grace_window.block2_num}
#     grace_in_effect = grace_window if grace_blocks - current_blocks else None

#     min_editable_block = current_window.block1_num
#     if grace_in_effect is not None:
#         min_editable_block = min(min_editable_block, grace_window.block1_num)

#     return current_window, min_editable_block, grace_in_effect