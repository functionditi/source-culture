// Flat alternating rectangles, following the supplied drawHDB study.
// CSS grid fills the available height without a canvas, brush library, or draw loop.
// Keep the accent distinct from all three appearance backgrounds, so changing
// appearance never makes the grid disappear and never needs a new random colour.
const paletteTokens = ['--caramel', '--rust', '--slate', '--sand', '--brick'];
const arrangements = [
  { units: [1, 4, 1, 2, 1], floors: Array(10).fill(1) },
  { units: [2, 3, .5, 2, 5, 2], floors: Array(6).fill(1) },
  { units: Array(12).fill(1), floors: [2, 2, .5, 2, 6, 2] },
].map(({ units, floors }) => ({
  // Repeat each pattern in both directions for a denser field of rectangles.
  units: [...units, ...units],
  floors: [...floors, ...floors],
}));

function readPalette(tokens = paletteTokens) {
  const style = getComputedStyle(document.documentElement);
  return tokens.map(token => style.getPropertyValue(token).trim());
}

function fillGrid(grid, { units, floors }, accent) {
  grid.setAttribute('aria-hidden', 'true');
  grid.style.setProperty('--grid-colour-a', 'var(--background)');
  grid.style.setProperty('--grid-colour-b', accent);
  grid.style.gridTemplateColumns = units.map(weight => `minmax(0, ${weight}fr)`).join(' ');
  grid.style.gridTemplateRows = floors.map(weight => `minmax(0, ${weight}fr)`).join(' ');
  const cells = document.createDocumentFragment();
  for (let floor = 0; floor < floors.length; floor++) {
    for (let unit = 0; unit < units.length; unit++) {
      const cell = document.createElement('span');
      cell.className = (floor + unit) % 2 ? 'grid-cell alternate' : 'grid-cell';
      cells.append(cell);
    }
  }
  grid.replaceChildren(cells);
}

export function mountColumnGrids(columns) {
  const availableColours = readPalette();
  const grids = columns.map((column, index) => {
    const grid = document.createElement('div');
    grid.className = 'column-grid';
    // Draw without replacement so the four bottom grids have distinct accents.
    const [accent] = availableColours.splice(Math.floor(Math.random() * availableColours.length), 1);
    fillGrid(grid, arrangements[index % arrangements.length], accent);
    column.append(grid);
    return grid;
  });
  return () => grids.forEach(grid => grid.remove());
}

export function mountWordmarkGrids(root) {
  const palette = readPalette(['--brick', '--rust']);
  root.querySelectorAll('[data-wordmark-grid]').forEach(grid => {
    fillGrid(grid, { units: [1, 4, 1, 2, 1], floors: [1, 1, 1, 1] }, palette[Math.floor(Math.random() * palette.length)]);
  });
}
