#!/usr/bin/env python3
"""
Anthu v2 — An esoteric programming language where information decays through noise.

A fraction is a program. The interpreter decodes it via the Euclidean algorithm
and executes an instruction set grounded in Shannon's information theory.

Each memory cell holds a (signal, noise) pair. Channel capacity C = log₂(1 + s/n)
governs loop control and output fidelity.

Named after Anthuphairesis (ἀνθυφαίρεσις) — the ancient Greek method of
reciprocal subtraction, ancestor of the Euclidean algorithm.
"""

import sys
import math
from fractions import Fraction


# ═══════════════════════════════════════════════════════════════════════
# Command Set (mod 10)
# ═══════════════════════════════════════════════════════════════════════

AMPLIFY     = 0   # s += 1
ATTENUATE   = 1   # s -= 1
INJECT      = 2   # n += 1
FILTER      = 3   # n -= 1  (min 0)
MOVE_RIGHT  = 4   # pointer →
MOVE_LEFT   = 5   # pointer ←
LOOP_START  = 6   # enter if C > 1
LOOP_END    = 7   # repeat if C > 1
MEASURE     = 8   # output min(s, floor(2^C))
LISTEN      = 9   # input → (s=ASCII, n=0)

CMD_NAMES = [
    'amplify', 'attenuate', 'inject', 'filter',
    'move→', 'move←', '[loop', 'loop]',
    'measure', 'listen'
]


# ═══════════════════════════════════════════════════════════════════════
# Information Theory
# ═══════════════════════════════════════════════════════════════════════

def channel_capacity(s, n):
    """Shannon channel capacity: C = log₂(1 + s/n)

    - n = 0, s > 0  →  C = ∞  (perfect channel)
    - s ≤ 0          →  C = 0  (no signal)
    - otherwise      →  C = log₂(1 + s/n)
    """
    if s <= 0:
        return 0.0
    if n <= 0:
        return float('inf')
    return math.log2(1 + s / n)


def observable_value(s, n):
    """Value observable through the channel, limited by capacity.

    output = min(s, floor(2^C)) = min(s, floor(1 + s/n)) = min(s, (s+n)//n)
    Uses integer arithmetic to avoid floating-point drift.
    """
    if s <= 0:
        return 0
    if n <= 0:
        return s
    return min(s, (s + n) // n)


# ═══════════════════════════════════════════════════════════════════════
# Codec — Euclidean Algorithm ↔ Continued Fraction
# ═══════════════════════════════════════════════════════════════════════

def decode(p, q):
    """Decode fraction p/q → command sequence via Euclidean algorithm."""
    commands = []
    while q > 0:
        quotient, remainder = divmod(p, q)
        commands.append(quotient % 10)
        p, q = q, remainder
    return commands


def encode(commands):
    """Encode command sequence → fraction p/q via continued fraction.

    Each command c_i becomes a quotient a_i where a_i mod 10 = c_i.
    For i ≥ 1, a_i must be ≥ 1, so c_i = 0 maps to a_i = 10.
    """
    if not commands:
        return Fraction(0, 1)

    quotients = []
    for i, cmd in enumerate(commands):
        if i == 0:
            quotients.append(cmd)
        else:
            quotients.append(cmd if cmd >= 1 else 10)

    if len(quotients) == 1:
        return Fraction(quotients[0], 1)

    # Convergent recurrence
    h_prev, h_curr = 1, quotients[0]
    k_prev, k_curr = 0, 1

    for i in range(1, len(quotients)):
        a = quotients[i]
        h_prev, h_curr = h_curr, a * h_curr + h_prev
        k_prev, k_curr = k_curr, a * k_curr + k_prev

    return Fraction(h_curr, k_curr)


# ═══════════════════════════════════════════════════════════════════════
# Bracket Matching
# ═══════════════════════════════════════════════════════════════════════

def match_brackets(commands):
    """Build bidirectional map of matching [ ] positions."""
    stack = []
    pairs = {}
    for i, cmd in enumerate(commands):
        if cmd == LOOP_START:
            stack.append(i)
        elif cmd == LOOP_END:
            if not stack:
                raise SyntaxError(f"Unmatched ] at position {i}")
            j = stack.pop()
            pairs[j] = i
            pairs[i] = j
    if stack:
        raise SyntaxError(f"Unmatched [ at position {stack[-1]}")
    return pairs


# ═══════════════════════════════════════════════════════════════════════
# Virtual Machine
# ═══════════════════════════════════════════════════════════════════════

class AnthuVM:
    """Anthu v2 virtual machine.

    Memory: sparse infinite tape of (signal, noise) cells.
    Control: loop entry/exit governed by channel capacity.
    Output: signal value limited by channel fidelity.
    """

    def __init__(self, commands, debug=False):
        self.commands = commands
        self.brackets = match_brackets(commands)
        self.tape = {}
        self.ptr = 0
        self.ip = 0
        self.debug = debug
        self.output_buffer = []

    def _cell(self):
        if self.ptr not in self.tape:
            self.tape[self.ptr] = [0, 0]
        return self.tape[self.ptr]

    def _trace(self, cmd):
        cell = self._cell()
        c = channel_capacity(cell[0], cell[1])
        c_str = '∞' if c == float('inf') else f'{c:.3f}'
        print(
            f"  ip={self.ip:4d}  {CMD_NAMES[cmd]:10s}  "
            f"ptr={self.ptr}  ({cell[0]}, {cell[1]})  C={c_str}",
            file=sys.stderr
        )

    def run(self):
        while self.ip < len(self.commands):
            cmd = self.commands[self.ip]
            cell = self._cell()

            if cmd == AMPLIFY:
                cell[0] += 1

            elif cmd == ATTENUATE:
                cell[0] -= 1

            elif cmd == INJECT:
                cell[1] += 1

            elif cmd == FILTER:
                cell[1] = max(0, cell[1] - 1)

            elif cmd == MOVE_RIGHT:
                self.ptr += 1

            elif cmd == MOVE_LEFT:
                self.ptr = max(0, self.ptr - 1)

            elif cmd == LOOP_START:
                # C > 1  ⟺  s > n  (integer comparison, no float needed)
                if not (cell[0] > cell[1]):
                    self.ip = self.brackets[self.ip]

            elif cmd == LOOP_END:
                if cell[0] > cell[1]:
                    self.ip = self.brackets[self.ip]

            elif cmd == MEASURE:
                val = observable_value(cell[0], cell[1])
                ch = chr(val % 128) if val >= 0 else chr(0)
                print(ch, end='', flush=True)
                self.output_buffer.append(ch)

            elif cmd == LISTEN:
                ch = sys.stdin.read(1)
                if ch:
                    cell[0] = ord(ch)
                    cell[1] = 0
                else:
                    cell[0] = 0
                    cell[1] = 0

            if self.debug:
                self._trace(cmd)

            self.ip += 1

        return ''.join(self.output_buffer)


# ═══════════════════════════════════════════════════════════════════════
# Assembler
# ═══════════════════════════════════════════════════════════════════════

SYMBOL_MAP = {
    '+': AMPLIFY,     '-': ATTENUATE,
    '!': INJECT,      '~': FILTER,
    '>': MOVE_RIGHT,  '<': MOVE_LEFT,
    '[': LOOP_START,  ']': LOOP_END,
    '.': MEASURE,     ',': LISTEN,
}

WORD_MAP = {
    'amplify': AMPLIFY,     'amp': AMPLIFY,
    'attenuate': ATTENUATE, 'att': ATTENUATE,
    'inject': INJECT,       'inj': INJECT,
    'filter': FILTER,       'fil': FILTER,
    'right': MOVE_RIGHT,    'left': MOVE_LEFT,
    'loop': LOOP_START,     'end': LOOP_END,
    'measure': MEASURE,     'mes': MEASURE,
    'listen': LISTEN,       'lis': LISTEN,
}

ALL_COMMANDS = {**SYMBOL_MAP, **WORD_MAP}


def assemble(text):
    """Parse assembly text into command list.

    Syntax:
        Symbols:   + - ! ~ > < [ ] . ,
        Words:     amplify, attenuate, inject, filter, ...
        Repeat:    +72  (72 amplifies)  or  amp*5  (5 amplifies)
        Comments:  # or //
    """
    commands = []

    lines = []
    for line in text.split('\n'):
        for marker in ('//', '#'):
            if marker in line:
                line = line[:line.index(marker)]
        lines.append(line)

    tokens = ' '.join(lines).split()

    for token in tokens:
        t = token.strip()
        if not t:
            continue

        tl = t.lower()

        # Exact match
        if tl in ALL_COMMANDS:
            commands.append(ALL_COMMANDS[tl])
            continue

        # Symbol + repeat:  +72, !5, >3
        if len(t) > 1 and t[0] in SYMBOL_MAP and t[1:].isdigit():
            commands.extend([SYMBOL_MAP[t[0]]] * int(t[1:]))
            continue

        # Word * repeat:  amp*72, inject*5
        if '*' in tl:
            parts = tl.split('*', 1)
            if parts[0] in ALL_COMMANDS and parts[1].isdigit():
                commands.extend([ALL_COMMANDS[parts[0]]] * int(parts[1]))
                continue

        raise ValueError(f"Unknown token: '{token}'")

    return commands


def disassemble(commands):
    """Pretty-print a command sequence."""
    lines = []
    for i, cmd in enumerate(commands):
        lines.append(f"  {i:4d}  {cmd}  {CMD_NAMES[cmd]}")
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

USAGE = """\
Anthu v2 — A fraction is a program. Information decays through noise.

Usage:
  anthu run <fraction | file.ant> [--debug]   Run program from fraction
  anthu asm <source.asm> [--debug]            Run program from assembly
  anthu compile <source.asm> <output.ant>     Compile assembly → fraction
  anthu decode <fraction>                     Disassemble a fraction

Examples:
  python anthu.py run 355/113
  python anthu.py asm examples/hello.asm
  python anthu.py compile examples/hello.asm hello.ant
  python anthu.py decode 355/113
"""


def parse_fraction(text):
    text = text.strip()
    if '/' in text:
        p, q = text.split('/', 1)
        return int(p), int(q)
    return int(text), 1


def cmd_run(args):
    if not args:
        print("Error: specify a fraction or .ant file", file=sys.stderr)
        return 1

    debug = '--debug' in args
    target = [a for a in args if a != '--debug'][0]

    if target.endswith('.ant'):
        with open(target, encoding='utf-8') as f:
            content = f.read().strip()
        p, q = parse_fraction(content)
    else:
        p, q = parse_fraction(target)

    commands = decode(p, q)

    if debug:
        print(f"[decode] {len(commands)} commands from {p}/{q}\n",
              file=sys.stderr)

    vm = AnthuVM(commands, debug=debug)
    vm.run()
    return 0


def cmd_asm(args):
    if not args:
        print("Error: specify source file", file=sys.stderr)
        return 1

    debug = '--debug' in args
    source = [a for a in args if a != '--debug'][0]

    with open(source, encoding='utf-8') as f:
        text = f.read()

    commands = assemble(text)

    if debug:
        print(f"[asm] {len(commands)} commands\n", file=sys.stderr)

    vm = AnthuVM(commands, debug=debug)
    vm.run()
    return 0


def cmd_compile(args):
    if len(args) < 2:
        print("Error: specify source and output files", file=sys.stderr)
        return 1

    source, output = args[0], args[1]

    with open(source, encoding='utf-8') as f:
        text = f.read()

    commands = assemble(text)
    frac = encode(commands)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(f"{frac.numerator}/{frac.denominator}\n")

    print(f"Compiled {len(commands)} commands → {output}")
    print(f"  {frac.numerator}/{frac.denominator}")
    return 0


def cmd_decode(args):
    if not args:
        print("Error: specify a fraction", file=sys.stderr)
        return 1

    p, q = parse_fraction(args[0])
    commands = decode(p, q)

    print(f"Fraction : {p}/{q}")
    print(f"Commands : {len(commands)}\n")
    print(disassemble(commands))
    return 0


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return 0

    mode = sys.argv[1].lower()
    args = sys.argv[2:]

    dispatch = {
        'run': cmd_run,
        'asm': cmd_asm,
        'compile': cmd_compile,
        'decode': cmd_decode,
    }

    handler = dispatch.get(mode)
    if handler:
        return handler(args)
    else:
        print(USAGE)
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
