"""
Set up a SimpleBoard with custom default values.
"""

from gem5.components.boards.simple_board import SimpleBoard
from m5.objects import NULL


class CustomSimpleBoard(SimpleBoard):
    def __init__(
        self,
        # FIXME TODO: Set this appropriately to match the CPU.
        #
        # Hint: gem5 uunderstands text labels, e.g., "800MHz"
        clk_freq: str = '4GHz',
        processor=NULL,
        memory=NULL,
        cache_hierarchy=NULL,
    ):
        super().__init__(
            clk_freq=clk_freq,
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
        )
