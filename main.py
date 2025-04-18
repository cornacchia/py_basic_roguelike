#!/usr/bin/env python3
import traceback

import tcod
from tcod import libtcodpy

import color
import exceptions
import input_handlers
import setup_game

def load_customfont(tileset):
  #The index of the first custom tile in the file
  a = 256

  # Graphical tiles start at row 5
  for y in range(5,6):
    # Rows are 32 tiles long
    for x in range(32):
      tileset.remap(a, x, y)
      a += 1

def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
  if isinstance(handler, input_handlers.EventHandler):
    handler.engine.save_as(filename)
    print("Game saved.")

def main() -> None:
  screen_width = 80
  screen_height = 50

  # tileset = libtcodpy.console_set_custom_font('graphical_tileset.png', libtcodpy.FONT_TYPE_GREYSCALE | libtcodpy.FONT_LAYOUT_TCOD, 32, 10)
  tileset = tcod.tileset.load_tilesheet(
    "graphical_tileset.png", 32, 10, tcod.tileset.CHARMAP_TCOD
  )
  load_customfont(tileset)

  handler: input_handlers.BaseEventHandler = setup_game.MainMenu()

  with tcod.context.new_terminal(
    screen_width,
    screen_height,
    tileset=tileset,
    title="",
    vsync=True,
  ) as context:
    root_console = tcod.console.Console(screen_width, screen_height, order="F")
    try:
      while True:
        root_console.clear()
        handler.on_render(console=root_console)
        context.present(root_console)

        try:
          for event in tcod.event.wait():
            context.convert_event(event)
            handler = handler.handle_events(event)
        except Exception:
          traceback.print_exc()
          if isinstance(handler, input_handlers.EventHandler):
            handler.engine.message_log.add_message(traceback.format_exc(), color.error)
    except exceptions.QuitWithoutSaving:
      raise
    except SystemExit:
      save_game(handler, "savegame.sav")
      raise
    except BaseException:
      save_game(handler, "savegame.sav")
      raise



if __name__ == "__main__":
  main()