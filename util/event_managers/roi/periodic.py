"""
Handle ROIs in a sampled, periodic manner.

(1) Fast-forward for <init-ff-interval> instructions.
(2) For each ROI:
    (a) Fast-forward for <ff-interval> instructions.
    (b) Switch to the ROI CPU and warm up for <warmup-interval> instructions.
    (c) Collect stats for <roi-interval> instructions.
(3) Repeat (2) until <num-rois> ROIs have been completed.
"""

from enum import Enum
from typing import Any, Final, Optional, Tuple, override

from gem5.simulate.exit_event import ExitEvent
from termcolor import colored

import util.simarglib as simarglib
from util.event_managers.event_manager import (
    EventHandler,
    EventHandlerDict,
    EventManager,
    EventTime,
)
from util.verbose import vprint

DEFAULT_FF_INTERVAL: Final[float] = 1000.0  # M instructions
DEFAULT_WARMUP_INTERVAL: Final[float] = 200.0  # M instructions
DEFAULT_ROI_INTERVAL: Final[float] = 800.0  # M instructions
DEFAULT_INIT_FF_INTERVAL: Final[float] = 0.0  # M instructions

#
# ~~~ Arguments ~~~
#
parser = simarglib.add_parser("Periodic ROI Manager")
parser.add_argument(
    "--ff-interval",
    type=float,
    default=DEFAULT_FF_INTERVAL,
    help=(
        "How long to fast-forward between between ROIs, in millions of "
        f"instructions. (Default: {DEFAULT_FF_INTERVAL} M instructions)"
    ),
)
parser.add_argument(
    "--warmup-interval",
    type=float,
    default=DEFAULT_WARMUP_INTERVAL,
    help=(
        "How long to warm up the simulator after each fast-forward "
        "phase, in millions of instructions. (Default: "
        f"{DEFAULT_WARMUP_INTERVAL} M instructions)"
    ),
)
parser.add_argument(
    "--roi-interval",
    type=float,
    default=DEFAULT_ROI_INTERVAL,
    help=(
        "How long to run the simulator to collect ROI statistics "
        "for each ROI, in millions of instructions. (Default: "
        f"{DEFAULT_ROI_INTERVAL} M instructions)"
    ),
)
parser.add_argument(
    "--init-ff-interval",
    type=float,
    default=DEFAULT_INIT_FF_INTERVAL,
    help=(
        "How long to fast-forward for after starting the benchmark, in "
        "millions of instructions. (Default: "
        f"{DEFAULT_INIT_FF_INTERVAL} M instructions)"
    ),
)
parser.add_argument(
    "--num-rois",
    type=int,
    default=None,
    help=("Stop sampling after <num-rois> ROIs. (Default: unlimited)"),
)
parser.add_argument(
    "--start-on-workbegin",
    action="store_true",
    help=(
        "Wait for an m5.workbegin event before starting the first "
        "period. This is useful for FS simulations that must boot the "
        "kernel, or for annotated workloads which indicate the start of "
        "the representative region of execution with an m5.workbegin "
        "event. "
    ),
)
parser.add_argument(
    "--continue-sim",
    action="store_true",
    help=(
        "After ROI #<num-roi> finishes, continue fast-forward "
        "execution. (Default: end simulation)"
    ),
)


#
# ~~~ Argument helper functions ~~~
#
def get_simarglib_interval(key: str) -> int:
    """Get simarglib's value for an interval.

    :param key The name of the interval
    :return The integer value of the interval, in cycles
    """
    interval: Any = simarglib.get(key)

    # Check if integer is a float
    if not isinstance(interval, float):
        raise ValueError(
            f"{key} must be a float, was {type(interval)} with value {interval}"
        )

    # Check if interval is non-negative
    if interval < 0:
        raise ValueError(f"{key} cannot be negative, was {interval}")

    # Multiply interval by 1M to get integer number of cycles
    interval_: Final[int] = int(interval * 1_000_000)
    return interval_


#
# ~~~ Phases ~~~
#
class Phase(Enum):
    """Define phases of the periodic ROI manager."""

    # Not doing any meaningful work
    NO_WORK = 1

    # Initial fast-forward phase
    FF_INIT = 2

    # Sampled fast-forward phase
    FF_WORK = 3

    # Sampled warmup phase
    WARMUP = 4

    # Sampled region of interest (ROI) phase
    ROI = 5


#
# ~~~ Event Manager ~~~
#
class PeriodicROIManager(EventManager):
    def __init__(
        self,
        ff_interval: Optional[int] = None,
        warmup_interval: Optional[int] = None,
        roi_interval: Optional[int] = None,
        init_ff_interval: Optional[int] = None,
        num_rois: Optional[int] = None,
        continue_sim: Optional[bool] = None,
        start_on_workbegin: Optional[bool] = None,
    ) -> None:
        """Initialize the PeriodicROIManager.

        :param ff_interval The fast-forward interval, in instructions
        :param warmup_interval The warmup interval, in instructions
        :param roi_interval The ROI interval, in instructions
        :param init_ff_interval The initial fast-forward interval, in instructions
        :param num_rois The number of ROIs to run
        :param continue_sim Whether to continue simulation after ROIs finish
        :param start_on_workbegin Whether to wait for an m5.workbegin event
                                  before ending the initial fast-forward phase.
        """
        super().__init__()

        self._ff_interval: Final[int] = (
            ff_interval
            if ff_interval is not None
            else get_simarglib_interval("ff_interval")
        )
        self._warmup_interval: Final[int] = (
            warmup_interval
            if warmup_interval is not None
            else get_simarglib_interval("warmup_interval")
        )
        self._roi_interval: Final[int] = (
            roi_interval
            if roi_interval is not None
            else get_simarglib_interval("roi_interval")
        )
        self._init_ff_interval: Final[int] = (
            init_ff_interval
            if init_ff_interval is not None
            else get_simarglib_interval("init_ff_interval")
        )
        self._num_rois: Final[Optional[int]] = (
            num_rois if num_rois is not None else simarglib.get("num_rois")  # type: ignore
        )
        self._continue_sim: Final[bool] = (
            continue_sim if continue_sim is not None else simarglib.get("continue_sim")  # type: ignore
        )
        self._start_on_workbegin: Final[bool] = (
            start_on_workbegin
            if start_on_workbegin is not None
            else simarglib.get("start_on_workbegin")  # type: ignore
        )

        initial_phase, initial_event = self._get_initial_phase_and_event()

        self._completed_rois: int = 0
        self._current_phase = initial_phase
        self._next_event = initial_event

        vprint(f"Initial phase: {self._current_phase}")
        vprint(f"Initial event: {self._next_event}")

    def _get_initial_phase_and_event(self) -> Tuple[Phase, EventTime]:
        """Determine the initial phase of the simulation.

        :return The initial phase and event of the simulation
        """
        if self._start_on_workbegin:
            # Wait for workbegin event
            return (Phase.NO_WORK, EventTime())
        elif self._init_ff_interval > 0:
            # Initial fast-forward phase
            return (Phase.FF_INIT, EventTime(instruction=self._init_ff_interval))
        else:
            # Sampled fast-forward phase
            return (Phase.FF_WORK, EventTime(instruction=self._ff_interval))

    def _handle_max_insts(self) -> EventHandler:
        """Handle max instructions event, by moving to the next phase.

        :yield True if the simulation should end, False otherwise
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0

            # ROI -> FF_WORK (or end simulation)
            # Dump ROI stats and switch to fast-forward processor
            if self._current_phase == Phase.ROI:
                self.dump_stats()
                self._completed_rois += 1

                # Schedule end of FF_WORK interval (if not past MAX_ROIs)
                if self._num_rois and self._completed_rois >= self._num_rois:
                    if self._continue_sim:
                        print(
                            colored(
                                f"***Instruction {current_ins:,}:",
                                color="blue",
                                attrs=["bold"],
                            ),
                            colored(
                                "Completed all ROIs, fast-forwarding until completion.",
                                color="blue",
                            ),
                        )
                    else:
                        print(
                            colored(
                                f"***Instruction {current_ins:,}:",
                                color="blue",
                                attrs=["bold"],
                            ),
                            colored(
                                "Completed all ROIs, ending simulation.",
                                color="blue",
                            ),
                        )

                        # Clear unwanted final stats block
                        self.reset_stats()

                        # End simulation
                        yield True
                else:
                    print(
                        colored(
                            f"***Instruction {current_ins:,}:",
                            color="blue",
                            attrs=["bold"],
                        ),
                        colored(
                            f"Entering ROI #{self._completed_rois + 1} "
                            "fast-forward phase and switching to "
                            "fast-forward processor.",
                            color="blue",
                        ),
                    )
                    self.set_next_event(EventTime(instruction=self._ff_interval))

                self.switch_processor()
                self._current_phase = Phase.FF_WORK

            # WARMUP -> ROI
            # Reset stats and start ROI
            elif self._current_phase == Phase.WARMUP:
                print(
                    colored(
                        f"***Instruction {current_ins:,}:",
                        color="blue",
                        attrs=["bold"],
                    ),
                    colored(
                        f"Entering ROI #{self._completed_rois + 1} simulation phase",
                        color="blue",
                    ),
                )

                # Reset stats for ROI
                self.reset_stats()

                # Schedule end of ROI interval
                self._current_phase = Phase.ROI
                self.set_next_event(EventTime(instruction=self._roi_interval))

            # FF_WORK -> WARMUP
            # Switch to detailed processor and start warmup
            elif self._current_phase == Phase.FF_WORK:
                print(
                    colored(
                        f"***Instruction {current_ins:,}:",
                        color="blue",
                        attrs=["bold"],
                    ),
                    colored(
                        f"Entering ROI #{self._completed_rois + 1} "
                        "warmup phase and switching to detailed "
                        "processor.",
                        color="blue",
                    ),
                )
                self.switch_processor()

                # Schedule end of WARMUP interval
                self._current_phase = Phase.WARMUP
                self.set_next_event(EventTime(instruction=self._warmup_interval))

            # FF_INIT -> FF_WORK
            # Enter first sampled fast-forward phase
            elif self._current_phase == Phase.FF_INIT:
                print(
                    colored(
                        f"***Instruction {current_ins:,}:",
                        color="blue",
                        attrs=["bold"],
                    ),
                    colored(
                        f"Entering ROI #{self._completed_rois + 1} "
                        "fast-forward phase.",
                        color="blue",
                    ),
                )

                # Enter the first FF_WORK phase
                self._current_phase = Phase.FF_WORK

                # Schedule end of FF_WORK phase
                self.set_next_event(EventTime(instruction=self._ff_interval))

            # NO_WORK
            # Nothing to do! This can occur if:
            # - An m5.workend event arrived in the middle of a sample
            #   interval, leaving one scheduled maxinsts event.
            else:
                self.set_next_event(EventTime())

            yield False  # Continue simulation

    def _handle_workbegin(self) -> EventHandler:
        """Handle workbegin event, by entering the first fast-forward phase.

        :yield True if the simulation should end, False otherwise
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0
            if self._init_ff_interval:
                # Initial fast-forward
                # Don't switch the core, but set up next exit event
                print(
                    colored(
                        f"***Instruction {current_ins:,}:",
                        color="blue",
                        attrs=["bold"],
                    ),
                    colored(
                        "Entering initial fast-forward phase on m5.workbegin.",
                        color="blue",
                    ),
                )

                # Schedule end of FF_INIT interval
                self._current_phase = Phase.FF_INIT

                if self._next_event.instruction is None:
                    raise ValueError("Next event instruction is None")
                self._next_event = EventTime(
                    instruction=self._next_event.instruction + self._init_ff_interval
                )
            else:
                # No initial FF, we should start sampling iterations
                print(
                    colored(
                        f"***Instruction {current_ins:,}:",
                        color="blue",
                        attrs=["bold"],
                    ),
                    colored(
                        f"Entering fast-forward phase for ROI #{self._completed_rois + 1} on m5.workbegin.",
                        color="blue",
                    ),
                )

                # Schedule end of FF_WORK interval
                self._current_phase = Phase.FF_WORK
                self.set_next_event(EventTime(instruction=self._ff_interval))
            yield False  # Continue simulation

    def _handle_workend(self) -> EventHandler:
        """Handle workend event, by ending the sampling until
        a workbegin event occurs.

        :yield True if the simulation should end, False otherwise
        :raise ValueError if the simulator is not set
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0

            print(
                colored(
                    f"***Instruction {current_ins:,}:",
                    color="blue",
                    attrs=["bold"],
                ),
                colored(
                    "Stopping ROIs on m5.workend.",
                    color="blue",
                ),
            )

            # If we are in the middle of a ROI, dump stats
            if self._current_phase == Phase.ROI:
                self.dump_stats()
                self._completed_rois += 1

            # Clear unwanted final stats block
            self.reset_stats()
            self._current_phase = Phase.NO_WORK

            # Continue simulation
            yield False

    def _handle_exit(self) -> EventHandler:
        """Handle exit event, by ending the simulation.

        :yield True if the simulation should end, False otherwise
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0

            print(
                colored(
                    f"***Instruction {current_ins:,}:",
                    color="blue",
                    attrs=["bold"],
                ),
                colored(
                    "Ending simulation on m5.exit.",
                    color="blue",
                ),
            )

            # If we are in the middle of a ROI, dump stats
            if self._current_phase == Phase.ROI:
                self.dump_stats()
                self._completed_rois += 1

            # Clear unwanted final stats block
            self.reset_stats()

            # End simulation
            yield True

    @override
    def get_event_handlers(self) -> EventHandlerDict:
        """Get dictionary of event types -> handlers.

        :return A dictionary of this manager's event handlers
        """
        return {
            ExitEvent.MAX_INSTS: self._handle_max_insts(),
            ExitEvent.WORKBEGIN: self._handle_workbegin(),
            ExitEvent.WORKEND: self._handle_workend(),
            ExitEvent.EXIT: self._handle_exit(),
        }
