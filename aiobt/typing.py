from typing import Callable, Any, Tuple

IP = Tuple[str, int]
RequestHandler = Callable[[dict, IP], Any]
