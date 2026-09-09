# """
# schedule_merge.py — protects already-punched (PAST) blocks only.

# On every upload, any block at or after the current punch window's start
# (current window, the grace window if still in effect, and every future
# block) is free to change — those are legitimate forecast revisions. Only
# blocks whose time has already passed (below that cutoff) get forced back to
# the last *accepted* baseline for that entity+date, regardless of what value
# shows up in the newly uploaded file — whether that's an accidental edit or
# a deliberate one.
# """


# def merge_blocks(baseline_blocks: dict, uploaded_blocks: dict, min_editable_block: int):
#     """
#     baseline_blocks : dict[int, list[str]] — last accepted values (may be {} if no baseline yet)
#     uploaded_blocks : dict[int, list[str]] — values from the file just uploaded
#     min_editable_block : the cutoff block number. Any block number >= this
#         is free to change (current window, grace window, and all future
#         blocks). Any block number below this is treated as already past
#         and protected against unauthorized changes.

#     Returns (merged_blocks, discarded_block_nums)
#         merged_blocks     : dict[int, list[str]] to actually use/send
#         discarded_block_nums : sorted list of block numbers where the upload
#                                 tried to change a value in an already-past
#                                 block, and that change was reverted
#     """
#     all_block_nums = sorted(set(baseline_blocks) | set(uploaded_blocks))
#     merged = {}
#     discarded = []

#     for bn in all_block_nums:
#         uploaded_val = uploaded_blocks.get(bn)
#         baseline_val = baseline_blocks.get(bn)

#         if bn >= min_editable_block:
#             # Current window, grace window, or a future block — always
#             # editable. Take the newly uploaded value if present, otherwise
#             # fall back to whatever baseline had.
#             merged[bn] = uploaded_val if uploaded_val is not None else baseline_val
#         else:
#             # Already past — protected.
#             if baseline_val is not None:
#                 merged[bn] = baseline_val
#                 if uploaded_val is not None and uploaded_val != baseline_val:
#                     discarded.append(bn)
#             else:
#                 # No baseline to protect with (first time we've seen this
#                 # block) — accept whatever was uploaded.
#                 merged[bn] = uploaded_val

#     return merged, discarded