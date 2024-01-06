from __future__ import annotations

import os

from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union

from tcod import libtcodpy
import tcod.event
from tcod.event import MouseButtonDown

import actions
from actions import (
  Action,
  BumpAction,
  WaitAction,
  PickupAction,
  TakeStairsActions
)
import color
from entity import Item
import exceptions

if TYPE_CHECKING:
  from engine import Engine
  from entity import Item

MOVE_KEYS = {
  # Arrow keys.
  tcod.event.KeySym.UP: (0, -1),
  tcod.event.KeySym.DOWN: (0, 1),
  tcod.event.KeySym.LEFT: (-1, 0),
  tcod.event.KeySym.RIGHT: (1, 0),
  tcod.event.KeySym.HOME: (-1, -1),
  tcod.event.KeySym.END: (-1, 1),
  tcod.event.KeySym.PAGEUP: (1, -1),
  tcod.event.KeySym.PAGEDOWN: (1, 1),
  # Numpad keys.
  tcod.event.KeySym.KP_1: (-1, 1),
  tcod.event.KeySym.KP_2: (0, 1),
  tcod.event.KeySym.KP_3: (1, 1),
  tcod.event.KeySym.KP_4: (-1, 0),
  tcod.event.KeySym.KP_6: (1, 0),
  tcod.event.KeySym.KP_7: (-1, -1),
  tcod.event.KeySym.KP_8: (0, -1),
  tcod.event.KeySym.KP_9: (1, -1),
  # Vi keys.
  tcod.event.KeySym.h: (-1, 0),
  tcod.event.KeySym.j: (0, 1),
  tcod.event.KeySym.k: (0, -1),
  tcod.event.KeySym.l: (1, 0),
  tcod.event.KeySym.y: (-1, -1),
  tcod.event.KeySym.u: (1, -1),
  tcod.event.KeySym.b: (-1, 1),
  tcod.event.KeySym.n: (1, 1),
}

WAIT_KEYS = {
  tcod.event.KeySym.PERIOD,
  tcod.event.KeySym.KP_5,
  tcod.event.KeySym.CLEAR,
}

CONFIRM_KEYS = {
  tcod.event.KeySym.RETURN,
  tcod.event.KeySym.KP_ENTER
}

ActionOrHandler = Union[Action, "BaseEventHandler"]

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
  def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
    state = self.dispatch(event)
    if isinstance(state, BaseEventHandler):
      return state
    assert not isinstance(state, Action), f"{self!r} can not handle actions."
    return self

  def on_render(self, console: tcod.Console) -> None:
    raise NotImplementedError()

  def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
    raise SystemExit()

class EventHandler(BaseEventHandler):
  def __init__(self, engine: Engine):
    self.engine = engine

  def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
    action_or_state = self.dispatch(event)
    if isinstance(action_or_state, BaseEventHandler):
      return action_or_state
    if self.handle_action(action_or_state):
      # A valid action was performed
      if not self.engine.player.is_alive:
        # Player was killed during or after the action
        return GameOverEventHandler(self.engine)
      return MainGameEventHandler(self.engine)
    return self

  def handle_action(self, action: Optional[Action]) -> bool:
    if action is None:
      return False

    try:
      action.perform()
    except exceptions.Impossible as exc:
      self.engine.message_log.add_message(exc.args[0], color.impossible)
      return False

    self.engine.handle_enemy_turns()
    self.engine.update_fov()

    return True

  def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
    if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
      self.engine.mouse_location = event.tile.x, event.tile.y

  def on_render(self, console: tcod.console.Console) -> None:
    self.engine.render(console)

class AskUserEventHandler(EventHandler):
  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
    if event.sym in {
      tcod.event.KeySym.LSHIFT,
      tcod.event.KeySym.RSHIFT,
      tcod.event.KeySym.LCTRL,
      tcod.event.KeySym.RCTRL,
      tcod.event.KeySym.LALT,
      tcod.event.KeySym.RALT
    }:
      return None
    return self.on_exit()

  def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
    return self.on_exit()

  def on_exit(self) -> Optional[ActionOrHandler]:
    return MainGameEventHandler(self.engine)

class InventoryEventHandler(AskUserEventHandler):
  TITLE = "<missing title>"

  def on_render(self, console: tcod.Console) -> None:
    super().on_render(console)
    number_of_items_in_inventory = len(self.engine.player.inventory.items)

    height = number_of_items_in_inventory + 2

    if height <= 3:
      height = 3

    if self.engine.player.x <= 30:
      x = 40
    else:
      x = 0

    y = 0

    width = len(self.TITLE) + 4

    console.draw_frame(
      x=x,
      y=y,
      width=width,
      height=height,
      title=self.TITLE,
      clear=True,
      fg=(255, 255, 255),
      bg=(0, 0, 0)
    )

    if number_of_items_in_inventory > 0:
      for i, item in enumerate(self.engine.player.inventory.items):
        item_key = chr(ord("a") + i)
        console.print(x + 1, y + i + 1, f"{item_key} - {item.name}")
    else:
      console.print(x + 1, y + 1, "Empty.")

  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
    player = self.engine.player
    key = event.sym
    index = key - tcod.event.KeySym.a

    if 0 <= index <= 26:
      try:
        selected_item = player.inventory.items[index]
      except IndexError:
        self.engine.message_log.add_message("Invalid entry.", color.invalid)
        return None

      return self.on_item_selected(selected_item)
    return super().ev_keydown(event)

  def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
    raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
  TITLE = "Select an item to use"

  def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
    return item.consumable.get_action(self.engine.player)

class InventoryDropHanlder(InventoryEventHandler):
  TITLE = "Select an item to drop"

  def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
    return actions.DropItem(self.engine.player, item)

class MainGameEventHandler(EventHandler):
  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
    action: Optional[Action] = None

    # Get the pressed key
    key = event.sym
    modifier = event.mod

    player = self.engine.player

    if key == tcod.event.KeySym.PERIOD and modifier & (
      tcod.event.KeySym.LSHIFT | tcod.event.KeySym.RSHIFT
    ):
      return TakeStairsActions(player)

    # Movement keys
    if key in MOVE_KEYS:
      dx, dy = MOVE_KEYS[key]
      action = BumpAction(player, dx, dy)
    elif key in WAIT_KEYS:
      action = WaitAction(player)

    elif key == tcod.event.KeySym.ESCAPE:
      raise SystemExit()

    elif key == tcod.event.KeySym.v:
      return HistoryViewer(self.engine)
    elif key == tcod.event.KeySym.g:
      action = PickupAction(player)

    elif key == tcod.event.KeySym.i:
      return InventoryActivateHandler(self.engine)
    elif key == tcod.event.KeySym.d:
      return InventoryDropHanlder(self.engine)
    elif key == tcod.event.KeySym.SLASH:
      return LookHandler(self.engine)

    return action

class GameOverEventHandler(EventHandler):
  def on_quit(self) -> None:
    if os.path.exists("savegame.sav"):
      os.remove("savegame.sav")
    raise exceptions.QuitWithoutSaving()

  def ev_quit(self, event: tcod.event.Quit) -> None:
    self.on_quit()

  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
    if event.sym == tcod.event.KeySym.ESCAPE:
      self.on_quit()

CURSOR_Y_KEYS = {
  tcod.event.KeySym.UP: -1,
  tcod.event.KeySym.DOWN: 1,
  tcod.event.KeySym.PAGEUP: -10,
  tcod.event.KeySym.PAGEDOWN: 10,
}

class HistoryViewer(EventHandler):
  def __init__(self, engine: Engine):
    super().__init__(engine)
    self.log_length = len(engine.message_log.messages)
    self.cursor = self.log_length - 1

  def on_render(self, console: tcod.console.Console) -> None:
    super().on_render(console)  # Draw the main state as the background.

    log_console = tcod.console.Console(console.width - 6, console.height - 6)

    # Draw a frame with a custom banner title.
    log_console.draw_frame(0, 0, log_console.width, log_console.height)
    log_console.print_box(
      0, 0, log_console.width, 1, "┤Message history├", alignment=libtcodpy.CENTER
    )

    # Render the message log using the cursor parameter.
    self.engine.message_log.render_messages(
      log_console,
      1,
      1,
      log_console.width - 2,
      log_console.height - 2,
      self.engine.message_log.messages[: self.cursor + 1],
    )

    log_console.blit(console, 3, 3)

  def ev_keydown(self, event: tcod.event.KeyDown) -> MainGameEventHandler:
    # Fancy conditional movement to make it feel right.
    if event.sym in CURSOR_Y_KEYS:
      adjust = CURSOR_Y_KEYS[event.sym]
      if adjust < 0 and self.cursor == 0:
        # Only move from the top to the bottom when you're on the edge.
        self.cursor = self.log_length - 1
      elif adjust > 0 and self.cursor == self.log_length - 1:
        # Same with bottom to top movement.
        self.cursor = 0
      else:
        # Otherwise move while staying clamped to the bounds of the history log.
        self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
    elif event.sym == tcod.event.KeySym.HOME:
      self.cursor = 0  # Move directly to the top message.
    elif event.sym == tcod.event.KeySym.END:
      self.cursor = self.log_length - 1  # Move directly to the last message.
    else:  # Any other key moves back to the main game state.
      return MainGameEventHandler(self.engine)
    return None

class SelectIndexHandler(AskUserEventHandler):
  def __init__(self, engine: Engine):
    super().__init__(engine)
    player = self.engine.player
    engine.mouse_location = player.x, player.y

  def on_render(self, console: tcod.Console) -> None:
    super().on_render(console)
    x, y = self.engine.mouse_location
    console.rgb["bg"][x, y] = color.white
    console.rgb["fg"][x, y] = color.black

  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
    key = event.sym
    if key in MOVE_KEYS:
      modifier = 1
      if event.mod & (tcod.event.KeySym.LSHIFT | tcod.event.KeySym.RSHIFT):
        modifier *= 5
      if event.mod & (tcod.event.KeySym.LCTRL | tcod.event.KeySym.RCTRL):
        modifier *= 10
      if event.mod & (tcod.event.KeySym.LALT | tcod.event.KeySym.RALT):
        modifier *= 20

      x, y = self.engine.mouse_location
      dx, dy = MOVE_KEYS[key]
      x += dx * modifier
      y += dy * modifier
      x = max(0, min(x, self.engine.game_map.width - 1))
      y = max(0, min(y, self.engine.game_map.height - 1))
      self.engine.mouse_location = x, y
      return None
    elif key in CONFIRM_KEYS:
      return self.on_index_selected(*self.engine.mouse_location)
    return super().ev_keydown(event)

  def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
    if self.engine.game_map.in_bounds(*event.tile):
      if event.button == 1:
        return self.on_index_selected(*event.tile)
    return super().ev_mousebuttondown(event)

  def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
    raise NotImplementedError()

class LookHandler(SelectIndexHandler):
  def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
    return MainGameEventHandler(self.engine)

class SingleRangedAttackHandler(SelectIndexHandler):
  def __init__(self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]):
    super().__init__(engine)
    self.callback = callback

  def on_index_selected(self, x: int, y: int) -> Optional[Action]:
    return self.callback((x, y))

class AreaRangedAttackHandler(SelectIndexHandler):
  def __init__(self, engine: Engine, radius: int, callback: Callable[[Tuple[int, int]], Optional[Action]]):
    super().__init__(engine)
    self.radius = radius
    self.callback = callback

  def on_render(self, console: tcod.console) -> None:
    super().on_render(console)
    x, y = self.engine.mouse_location

    console.draw_frame(
      x = x - self.radius - 1,
      y = y - self.radius - 1,
      width = self.radius ** 2,
      height = self.radius ** 2,
      fg = color.red,
      clear = False
    )

  def on_index_selected(self, x: int, y: int) -> Optional[Action]:
    return self.callback((x, y))

class PopupMessage(BaseEventHandler):
  def __init__(self, parent_handler: BaseEventHandler, text: str):
    self.parent = parent_handler
    self.text = text

  def on_render(self, console: tcod.console) -> None:
    self.parent.on_render(console)
    console.rgb["fg"] //= 8
    console.rgb["bg"] //= 8

    console.print(
      console.width // 2,
      console.height // 2,
      self.text,
      fg=color.white,
      bg=color.black,
      alignment=libtcodpy.CENTER
    )

  def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
    return self.parent