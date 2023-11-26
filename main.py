#!/usr/bin/env python3
import tcod

from engine import Engine
from entity import Entity
from game_map import GameMap
from input_handlers import EventHandler


def main() -> None:
  screen_width = 80
  screen_height = 50

  map_width = 80
  map_height = 45

  event_handler = EventHandler()

  player_x = int(screen_width / 2)
  player_y = int(screen_height / 2)

  player = Entity(player_x, player_y, '@', (255, 255, 255))

  entities = { player }

  game_map = GameMap(map_width, map_height)

  engine = Engine(entities=entities, event_handler=event_handler, game_map=game_map, player=player)

  tileset = tcod.tileset.load_tilesheet(
    "tileset.png", 32, 8, tcod.tileset.CHARMAP_TCOD
  )


  with tcod.context.new_terminal(
    screen_width,
    screen_height,
    tileset=tileset,
    title="",
    vsync=True,
  ) as context:
    root_console = tcod.console.Console(screen_width, screen_height, order="F")
    while True:
      engine.render(console=root_console, context=context)
      events = tcod.event.wait()
      engine.handle_events(events)

if __name__ == "__main__":
  main()