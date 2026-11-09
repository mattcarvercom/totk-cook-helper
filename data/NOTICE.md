# Third-party data

`collectibles.json` contains coordinates and completion hashes for Tears of the
Kingdom collectibles. `map_regions.json` contains the surface Skyview Tower
regions and the Depths Field Map Areas used for map reveal. The values are facts
about the game and were compiled from the community projects below. No game art
or game files are included.

- [marcrobledo/savegame-editors](https://github.com/marcrobledo/savegame-editors)
  for the save hashes and completion research.
- [lud99/totk-unexplored](https://github.com/lud99/totk-unexplored) for the
  collected and checked coordinate data.
- [zeldamods/objmap-totk](https://github.com/zeldamods/objmap-totk) for the
  Skyview Tower region polygons and Depths Field Map Area polygons, extracted
  from the game's own map data, and
  [zeldamods/radar-totk](https://github.com/zeldamods/radar-totk) for the
  underlying object data.

The companion rebuilds all icons, names, and map tiles from the user's own
game files at install time. The collectible list and the region polygons are the
only pre-computed data files, and they are used read-only.
