"""
Sample FS config script to run single-threaded SPEC '06 and GAP
benchmarks with a switchable CPU, booting the OS in KVM and then
switching to an O3 Skylake procesor with a three-level classic cache
hierarchy
"""

import time
from typing import Final

from gem5.components.boards.x86_board import X86Board
from gem5.components.memory import DualChannelDDR4_2400
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires
from termcolor import colored

import util.simarglib as simarglib
from components.cache_hierarchies.three_level_classic import ThreeLevelClassicHierarchy
from components.cpus.skylake_cpu import SkylakeCPU
from components.processors.custom_x86_switchable_processor import (
    CustomX86SwitchableProcessor,
)
from util.event_managers.event_manager import EventCoordinator
from util.event_managers.roi.periodic import PeriodicROIManager
from workloads.fs.spec06_and_gap import Spec06AndGapFS

requires(isa_required=ISA.X86)

# Parse all command-line args
simarglib.parse()
verbose: Final[bool] = False

# Create a processor
# KVM start core, O3 switch core recommended
processor = CustomX86SwitchableProcessor(SwitchCPUCls=SkylakeCPU)

# Create a cache hierarchy
cache_hierarchy = ThreeLevelClassicHierarchy()

# Create some DRAM
memory = DualChannelDDR4_2400(size="3GiB")

# Create a board
board = X86Board(
    clk_freq="3GHz",
    processor=processor,
    cache_hierarchy=cache_hierarchy,
    memory=memory,
)

# Create ROI managers
roi_manager = PeriodicROIManager(verbose=verbose)
coordinator = EventCoordinator([roi_manager], verbose=verbose)

# Set up the workload
workload = Spec06AndGapFS()
board.set_workload(workload)

# Set up the simulator
simulator = Simulator(
    board=board,
    on_exit_event=coordinator.get_event_handlers(),
)

# Register event managers
coordinator.register(simulator)

# Run the simulation
print(
    colored(
        "***Beginning simulation!",
        color="blue",
        attrs=["bold"],
    )
)

start_wall_time: Final[float] = time.time()
simulator.run()
elapsed_wall_time: Final[float] = time.time() - start_wall_time
elapsed_instructions: Final[int] = coordinator.get_current_time().instruction or 0
elapsed_ticks: Final[int] = simulator.get_current_tick()

print(
    colored(
        f"***Instruction {elapsed_instructions:,}, tick {elapsed_ticks:,}:",
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
