import inspect
from types import FrameType
from typing import Any, Final

from termcolor import colored

import util.simarglib as simarglib

parser = simarglib.add_parser("Verbose Output")
parser.add_argument(
    "--verbose",
    action="store_true",
    help="Print verbose output for debugging",
)


def _get_frame_names(frame: FrameType | None) -> tuple[str, str]:
    """Get the class and function name from a frame.

    :param frame The frame to extract the names from
    :return The class and function name
    """
    if frame is None:
        return ("?", "?")

    caller: Final[FrameType | None] = frame.f_back
    if caller is None:
        return ("?", "?")

    inst: Final[Any] = caller.f_locals.get("self", None)
    if inst is None:
        return ("?", "?")

    class_name: Final[str] = inst.__class__.__name__
    func_name: Final[str] = caller.f_code.co_name

    return class_name, func_name


def vprint(*args: Any) -> None:
    """Print verbose information.

    :param func The function that is printing the information
    :param args The arguments to print
    """
    verbose: Final[bool] = simarglib.get("verbose") or False
    if not verbose:
        return

    # Infer the class and function name from the stack
    frame = inspect.currentframe()
    class_name, func_name = _get_frame_names(frame)

    # Print with decorated prefix of class and function name
    print(
        colored(
            f"[{class_name}.{func_name}]",
            color="grey",
            attrs=["bold"],
        ),
        colored(" ".join(map(str, args)), color="grey"),
    )
