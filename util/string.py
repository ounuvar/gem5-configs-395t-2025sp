import inspect
from typing import Any, Final, Optional

from termcolor import colored


def vprint(*args: Any) -> None:
    """Print verbose information.

    :param func The function that is printing the information
    :param args The arguments to print
    """
    # Infer the class and function name from the stack
    frame = inspect.currentframe()
    if frame is None:
        return

    caller = frame.f_back
    if caller is None:
        return

    inst = caller.f_locals.get("self", None)
    if inst is None:
        return

    verbose: Final[Optional[bool]] = getattr(inst, "_verbose", None)
    if verbose is None or verbose is False:
        return

    class_name: Final[str] = inst.__class__.__name__
    func_name: Final[str] = caller.f_code.co_name

    # Print with decorated prefix of class and function name
    print(
        colored(
            f"[{class_name}.{func_name}]",
            color="grey",
            attrs=["bold"],
        ),
        colored(" ".join(map(str, args)), color="grey"),
    )
