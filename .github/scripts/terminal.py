"""Generate an animated SVG terminal running a little git + vim session.

Usage: python terminal.py <output.svg>
Edit session() to change what gets typed.
"""
import sys
from html import escape

FONT, CW, LH = 14, 8.4, 20  # font size, char width (0.6em monospace), line height
W, H, PAD, TOP = 495, 250, 18, 52
TYPE_MS, ENTER_MS, HOLD_MS, RESET_MS = 55, 350, 3500, 600

# dracula palette
FG, DIM, PINK, PURPLE, GREEN, YELLOW, CYAN, RED = (
    "#f8f8f2", "#6272a4", "#ff79c6", "#bd93f9", "#50fa7b", "#f1fa8c", "#8be9fd", "#ff5555")


class Line:
    def __init__(self, row, segs):
        self.row, self.segs, self.steps = row, segs, []  # steps: [(ms, visible chars)]

    @property
    def size(self):
        return sum(len(s) for s, _ in self.segs)


class Term:
    def __init__(self):
        self.t, self.lines, self.cursor = 0, [], []  # cursor: [(ms, row, col)]

    def wait(self, ms):
        self.t += ms

    def move(self, row, col):
        self.cursor.append((self.t, row, col))

    def out(self, row, *segs):
        line = Line(row, list(segs))
        self.lines.append(line)
        self.show(line)
        return line

    def type(self, row, prompt, *segs):
        """Show `prompt` segments at once, then type `segs` char by char."""
        line = Line(row, list(prompt) + list(segs))
        self.lines.append(line)
        shown = sum(len(s) for s, _ in prompt)
        line.steps.append((self.t, shown))
        self.move(row, shown)
        for _ in range(line.size - shown):
            self.t += TYPE_MS
            shown += 1
            line.steps.append((self.t, shown))
            self.move(row, shown)
        self.t += ENTER_MS
        return line

    def show(self, *lines):
        for line in lines:
            line.steps.append((self.t, line.size))

    def hide(self, *lines):
        for line in lines:
            line.steps.append((self.t, 0))


def prompt(branch):
    return [("(", DIM), (branch, PURPLE), (") ", DIM), ("$ ", GREEN)]


def git(*args):
    return [("git", PINK), *args]


def session():
    term = Term()
    shell = [
        term.type(0, prompt("main"), *git((" checkout -b feat/term", FG))),
        term.out(1, ("Switched to a new branch 'feat/term'", FG)),
    ]
    term.wait(300)
    shell.append(term.type(2, prompt("feat/term"), ("vim", CYAN), (" README.md", FG)))

    # vim takes over the screen
    term.hide(*shell)
    vim = [
        term.out(0, ("# Hi, I'm Carlos", PURPLE)),
        term.out(1, ("Programmer from Mexico.", FG)),
        term.out(2, ("I code in Python, JS and Java.", FG)),
    ]
    tildes = [term.out(r, ("~", DIM)) for r in range(3, 9)]
    status = term.out(9, ('"README.md" 3L, 70B', FG))
    term.move(0, 0)
    term.wait(900)

    term.hide(status, tildes[0])
    insert = term.out(9, ("-- INSERT --", YELLOW))
    vim.append(term.type(3, [], ("Now with a git terminal :)", FG)))
    term.wait(500)

    term.hide(insert)
    vim.append(term.type(9, [], (":wq", FG)))
    term.hide(*vim, *tildes)

    # back in the shell
    term.show(*shell)
    branch = prompt("feat/term")
    term.type(3, branch, *git((" add README.md", FG)))
    term.type(4, branch, *git((" commit -m ", FG), ('"feat: git terminal"', YELLOW)))
    term.out(5, ("[feat/term ", FG), ("3f2a9c1", YELLOW), ("] feat: git terminal", FG))
    term.out(6, (" 1 file changed, ", FG), ("1 insertion(+)", GREEN))
    term.wait(400)
    term.type(7, branch, *git((" push -u origin feat/term", FG)))
    term.out(8, (" * [new branch]      ", GREEN), ("feat/term -> feat/term", FG))
    term.wait(200)
    term.type(9, branch)
    term.wait(HOLD_MS)
    return term


def discrete(steps, total, hidden="0"):
    """Build looping discrete SMIL values/keyTimes, `hidden` before the first step and after reset."""
    vals, keys = [hidden], [0.0]
    for ms, v in steps:
        k = round(ms / total, 5)
        if k <= keys[-1]:
            vals[-1] = v
        else:
            vals.append(v)
            keys.append(k)
    vals.append(hidden)
    keys.append(round((total - RESET_MS) / total, 5))
    return ";".join(vals), ";".join(f"{k:g}" for k in keys)


def render():
    term = session()
    total = term.t + RESET_MS
    dur = f"{total / 1000:.2f}s"

    def anim(attr, steps, hidden="0"):
        vals, keys = discrete(steps, total, hidden)
        return (f'<animate attributeName="{attr}" values="{vals}" keyTimes="{keys}" '
                f'dur="{dur}" calcMode="discrete" repeatCount="indefinite"/>')

    out = []
    for i, line in enumerate(term.lines):
        y = TOP + line.row * LH
        spans = "".join(f'<tspan fill="{c}">{escape(s)}</tspan>' for s, c in line.segs if s)
        length = f' textLength="{line.size * CW:.1f}" lengthAdjust="spacing"' if line.size else ""
        width = anim("width", [(ms, f"{c * CW:.1f}") for ms, c in line.steps])
        out.append(f"""
  <clipPath id="l{i}"><rect x="{PAD}" y="{y - 15}" height="{LH}" width="0">{width}</rect></clipPath>
  <text x="{PAD}" y="{y}" clip-path="url(#l{i})"{length}>{spans}</text>""")

    cx = anim("x", [(ms, f"{PAD + col * CW:.1f}") for ms, _, col in term.cursor], hidden="-20")
    cy = anim("y", [(ms, f"{TOP + row * LH - 13}") for ms, row, _ in term.cursor], hidden="-20")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Terminal running git and vim commands">
  <style>
    text {{ font: {FONT}px Consolas, 'DejaVu Sans Mono', Menlo, 'Courier New', monospace; white-space: pre; }}
  </style>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="#282a36" stroke="#44475a"/>
  <path d="M0.5 28V10.5a10 10 0 0 1 10-10h{W - 21}a10 10 0 0 1 10 10V28z" fill="#21222c"/>
  <circle cx="20" cy="14.5" r="5.5" fill="{RED}"/>
  <circle cx="38" cy="14.5" r="5.5" fill="{YELLOW}"/>
  <circle cx="56" cy="14.5" r="5.5" fill="{GREEN}"/>
  <text x="{W / 2}" y="19" text-anchor="middle" fill="{DIM}" style="font-size:12px">carlos@mexico: ~/IngMtzB</text>{''.join(out)}
  <rect width="{CW:.1f}" height="17" fill="{PINK}" x="-20" y="-20">
    {cx}
    {cy}
    <animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/>
  </rect>
</svg>
"""


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        f.write(render())
