"""
Sample SE config script to run a custom binary with a switchable CPU,
running periodic fast-forward intervals in KVM then switching to an O3
Skylake processor with a three-level classic cache hierarchy
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
from components.processors.custom_x86_switchable_processor import (
    CustomX86SwitchableProcessor,
)
from util.event_managers.event_manager import EventCoordinator
from util.event_managers.roi.periodic import PeriodicROIManager
from workloads.se.custom_binary import CustomBinarySE

requires(isa_required=ISA.X86)

# Parse all command-line args
simarglib.parse()

# Create a processor
# KVM start core, O3 switch core recommended
processor = CustomX86SwitchableProcessor(SwitchCPUCls=SkylakeCPU)

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

# Create event manager and event coordinator
#
# This specific event manager, PeriodicROIManager, handles the
# fast-forward, warmup, and simulation intervals / regions of interest.
#
# The coordinator manages one or more event managers to ensure multiple
# event managers can work together smoothly.
roi_manager = PeriodicROIManager()
coordinator = EventCoordinator([roi_manager])

# Set up the workload
workload = CustomBinarySE()
board.set_workload(workload)

# Set up the simulator
simulator = Simulator(
    board=board,
    on_exit_event=coordinator.get_event_handlers(),
)

# Register event managers
coordinator.register(simulator)

# Print information
print(
    colored(
        "***Fast-forward interval:",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._ff_interval:,} instructions",
        color="blue",
    ),
)
print(
    colored(
        "***Warmup interval      :",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._warmup_interval:,} instructions",
        color="blue",
    ),
)
print(
    colored(
        "***ROI interval         :",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._roi_interval:,} instructions",
        color="blue",
    ),
)
print(
    colored(
        "***Initial fast-forward :",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._init_ff_interval:,} instructions",
        color="blue",
    ),
)
print(
    colored(
        "***Maximum ROIs         :",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._num_rois or 'Unlimited'}",
        color="blue",
    ),
)
print(
    colored(
        "***Start on m5.workbegin:",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._start_on_workbegin}",
        color="blue",
    ),
)
print(
    colored(
        "***Continue simulation  :",
        color="blue",
        attrs=["bold"],
    ),
    colored(
        f"{roi_manager._continue_sim}",
        color="blue",
    ),
)

# Run the simulation
print(
    colored(
        "***Beginning simulation!",
        color="blue",
        attrs=["bold"],
    ),
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
