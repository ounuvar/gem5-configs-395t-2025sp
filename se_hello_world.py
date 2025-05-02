"""
Sample SE config script to run a Hello World program on an O3 Skylake
processor with a three-level classic cache hierarchy
"""

import time
from typing import Final

from gem5.components.memory import DualChannelDDR4_2400
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires
from termcolor import colored

import util.simarglib as simarglib
from components.boards.custom_simple_board import CustomSimpleBoard
from components.cache_hierarchies.three_level_classic import ThreeLevelClassicHierarchy
from components.cpus.skylake_cpu import SkylakeCPU
from components.processors.custom_x86_processor import CustomX86Processor
from workloads.se.hello_world import HelloWorldSE

requires(isa_required=ISA.X86)

# Parse all command-line args
simarglib.parse()

# Create a processor
# O3 core type recommended
processor = CustomX86Processor(CPUCls=SkylakeCPU)

# Create a cache hierarchy
cache_hierarchy = ThreeLevelClassicHierarchy()

# Create some DRAM
memory = DualChannelDDR4_2400(size="3GiB")

# Create a board
board = CustomSimpleBoard(
    processor=processor,
    cache_hierarchy=cache_hierarchy,
    memory=memory,
)

# Set up the workload
workload = HelloWorldSE()
board.set_workload(workload)

# Set up the simulator
simulator = Simulator(board=board)

# Run the simulation
print(
    colored(
        "***Beginning simulation!",
        color="blue",
        attrs=["bold"],
    )
)

start_wall_time = time.time()
simulator.run()
elapsed_wall_time = time.time() - start_wall_time
elapsed_ticks: Final[int] = simulator.get_current_tick()

print(
    colored(
        f"***Tick {elapsed_ticks:,}:",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"Simulator exited because {simulator.get_last_exit_event_cause()}.",
        color="blue",
    ),
)
print(
    colored(
        "***Total wall clock time:",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{(elapsed_wall_time/60):.2f} min",
        color="blue",
    ),
)
