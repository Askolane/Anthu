#!/usr/bin/env python3
"""
Anthuc — High-level compiler for Anthu v2.

Compiles a readable, information-theory-themed language into
Anthu assembly (and optionally into a single fraction).

Example:
    channel msg
    signal msg = 72
    measure msg          // outputs 'H'

    emit "Hello, World!"

    channel counter
    signal counter = 10
    while counter {
        inject counter * 2
    }
"""

import sys
import re
from anthu import assemble, encode, AnthuVM, decode


# ═══════════════════════════════════════════════════════════════════════
# Compiler State
# ═══════════════════════════════════════════════════════════════════════

class Compiler:
    def __init__(self):
        self.channels = {}      # name → cell index
        self.next_cell = 0      # next available cell
        self.current_cell = 0   # current pointer position
        self.asm_lines = []     # generated assembly lines
        self.errors = []

    def _alloc(self, name):
        """Allocate a cell for a channel name."""
        if name in self.channels:
            return self.channels[name]
        idx = self.next_cell
        self.channels[name] = idx
        self.next_cell += 1
        return idx

    def _move_to(self, target):
        """Emit move commands to reach target cell."""
        diff = target - self.current_cell
        if diff > 0:
            self.asm_lines.append(f">{diff}")
        elif diff < 0:
            self.asm_lines.append(f"<{-diff}")
        self.current_cell = target

    def _emit(self, asm):
        """Emit raw assembly."""
        self.asm_lines.append(asm)

    def _emit_comment(self, text):
        """Emit a comment line."""
        self.asm_lines.append(f"# {text}")

    # ───────────────────────────────────────────────────────────────
    # Statement compilers
    # ───────────────────────────────────────────────────────────────

    def compile_channel(self, name):
        """Declare a named channel (allocate a cell)."""
        self._alloc(name)
        self._emit_comment(f"channel {name} → cell {self.channels[name]}")

    def compile_signal(self, name, value):
        """Set a channel's signal to a value."""
        idx = self._alloc(name)
        self._move_to(idx)
        if value >= 0:
            self._emit(f"+{value}")
        else:
            self._emit(f"-{-value}")

    def compile_noise(self, name, value):
        """Set a channel's noise to a value."""
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(f"!{value}")

    def compile_amplify(self, name, amount=1):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(f"+{amount}")

    def compile_attenuate(self, name, amount=1):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(f"-{amount}")

    def compile_inject(self, name, amount=1):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(f"!{amount}")

    def compile_filter(self, name, amount=1):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(f"~{amount}")

    def compile_measure(self, name):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(".")

    def compile_listen(self, name):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit(",")

    def compile_emit(self, text):
        """Emit a string literal. Uses a scratch cell."""
        # Process escape sequences
        text = (text
                .replace('\\n', '\n')
                .replace('\\t', '\t')
                .replace('\\\\', '\\')
                .replace('\\"', '"'))
        scratch = self._alloc("__emit_scratch__")
        self._emit_comment(f'emit string')
        for ch in text:
            self._move_to(scratch)
            code = ord(ch)
            # Reset cell: we need to zero it first
            # Use a loop to drain signal, then set fresh
            # Simple approach: use a fresh cell each time
            self._emit(f"+{code} .")
            # Reset for next char: attenuate back to 0
            self._emit(f"-{code}")

    def compile_while_start(self, name):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit("[")

    def compile_while_end(self, name):
        idx = self._alloc(name)
        self._move_to(idx)
        self._emit("]")

    def compile_copy(self, src, dst):
        """Copy signal from src to dst using a temp cell.

        Algorithm:
        1. Allocate temp cell
        2. Loop on src: decrement src, increment dst and temp
        3. Loop on temp: decrement temp, increment src (restore)
        """
        src_idx = self._alloc(src)
        dst_idx = self._alloc(dst)
        tmp = self._alloc(f"__copy_tmp_{src}_{dst}__")

        self._emit_comment(f"copy {src} → {dst}")

        # Phase 1: drain src into dst + tmp
        self._move_to(src_idx)
        self._emit("[")  # while src has signal
        self._emit("-")  # src.s -= 1

        self._move_to(dst_idx)
        self._emit("+")  # dst.s += 1

        self._move_to(tmp)
        self._emit("+")  # tmp.s += 1

        self._move_to(src_idx)
        self._emit("]")

        # Phase 2: restore src from tmp
        self._move_to(tmp)
        self._emit("[")
        self._emit("-")

        self._move_to(src_idx)
        self._emit("+")

        self._move_to(tmp)
        self._emit("]")

    # ───────────────────────────────────────────────────────────────
    # Parser
    # ───────────────────────────────────────────────────────────────

    def parse_and_compile(self, source):
        """Parse high-level source and compile to assembly."""
        lines = source.split('\n')
        while_stack = []  # track nested while channel names

        for lineno, raw_line in enumerate(lines, 1):
            # Strip comments
            line = raw_line
            for marker in ('//', '#'):
                if marker in line:
                    line = line[:line.index(marker)]
            line = line.strip()
            if not line:
                continue

            try:
                self._parse_line(line, lineno, while_stack)
            except Exception as e:
                self.errors.append(f"Line {lineno}: {e}")

        if while_stack:
            self.errors.append(
                f"Unclosed while block(s): {', '.join(while_stack)}")

        return self.errors

    def _parse_line(self, line, lineno, while_stack):
        tokens = line.split()
        cmd = tokens[0].lower()

        if cmd == 'channel':
            # channel <name>
            if len(tokens) < 2:
                raise ValueError("channel requires a name")
            self.compile_channel(tokens[1])

        elif cmd == 'signal':
            # signal <name> = <value>
            match = re.match(r'signal\s+(\w+)\s*=\s*(-?\d+)', line, re.I)
            if not match:
                raise ValueError("expected: signal <name> = <value>")
            self.compile_signal(match.group(1), int(match.group(2)))

        elif cmd == 'noise':
            # noise <name> = <value>
            match = re.match(r'noise\s+(\w+)\s*=\s*(\d+)', line, re.I)
            if not match:
                raise ValueError("expected: noise <name> = <value>")
            self.compile_noise(match.group(1), int(match.group(2)))

        elif cmd == 'amplify':
            # amplify <name> [* <n>]
            name, amount = self._parse_name_amount(tokens[1:])
            self.compile_amplify(name, amount)

        elif cmd == 'attenuate':
            # attenuate <name> [* <n>]
            name, amount = self._parse_name_amount(tokens[1:])
            self.compile_attenuate(name, amount)

        elif cmd == 'inject':
            # inject <name> [* <n>]
            name, amount = self._parse_name_amount(tokens[1:])
            self.compile_inject(name, amount)

        elif cmd == 'filter':
            # filter <name> [* <n>]
            name, amount = self._parse_name_amount(tokens[1:])
            self.compile_filter(name, amount)

        elif cmd == 'measure':
            # measure <name>
            if len(tokens) < 2:
                raise ValueError("measure requires a channel name")
            self.compile_measure(tokens[1])

        elif cmd == 'listen':
            # listen <name>
            if len(tokens) < 2:
                raise ValueError("listen requires a channel name")
            self.compile_listen(tokens[1])

        elif cmd == 'emit':
            # emit "string"
            match = re.match(r'emit\s+"([^"]*)"', line, re.I)
            if not match:
                raise ValueError('expected: emit "string"')
            self.compile_emit(match.group(1))

        elif cmd == 'copy':
            # copy <src> -> <dst>
            match = re.match(r'copy\s+(\w+)\s*->\s*(\w+)', line, re.I)
            if not match:
                raise ValueError("expected: copy <src> -> <dst>")
            self.compile_copy(match.group(1), match.group(2))

        elif cmd == 'while':
            # while <name> {
            match = re.match(r'while\s+(\w+)\s*\{?', line, re.I)
            if not match:
                raise ValueError("expected: while <name> {")
            name = match.group(1)
            while_stack.append(name)
            self.compile_while_start(name)

        elif cmd == '}':
            if not while_stack:
                raise ValueError("unexpected }")
            name = while_stack.pop()
            self.compile_while_end(name)

        else:
            raise ValueError(f"unknown command: {cmd}")

    def _parse_name_amount(self, tokens):
        """Parse 'name' or 'name * N' from token list."""
        if not tokens:
            raise ValueError("expected channel name")
        name = tokens[0]
        amount = 1
        if len(tokens) >= 3 and tokens[1] == '*':
            amount = int(tokens[2])
        elif len(tokens) >= 2 and tokens[1].startswith('*'):
            amount = int(tokens[1][1:])
        return name, amount

    def get_assembly(self):
        """Return the generated assembly as a string."""
        return '\n'.join(self.asm_lines)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

USAGE = """\
Anthuc — High-level compiler for Anthu v2.

Usage:
  anthuc run <source.anth>              Compile and execute
  anthuc compile <source.anth> <out>    Compile to assembly (.asm) or fraction (.ant)
  anthuc debug <source.anth>            Show generated assembly

Examples:
  python anthuc.py run examples/hello.anth
  python anthuc.py compile examples/hello.anth hello.asm
  python anthuc.py compile examples/hello.anth hello.ant
  python anthuc.py debug examples/hello.anth
"""


def compile_source(source_text):
    """Compile high-level source → (assembly_text, commands, errors)."""
    compiler = Compiler()
    errors = compiler.parse_and_compile(source_text)
    if errors:
        return None, None, errors
    asm_text = compiler.get_assembly()
    commands = assemble(asm_text)
    return asm_text, commands, []


def cmd_run(args):
    if not args:
        print("Error: specify source file", file=sys.stderr)
        return 1

    with open(args[0]) as f:
        source = f.read()

    asm_text, commands, errors = compile_source(source)
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    vm = AnthuVM(commands)
    vm.run()
    return 0


def cmd_compile(args):
    if len(args) < 2:
        print("Error: specify source and output files", file=sys.stderr)
        return 1

    source_path, output_path = args[0], args[1]

    with open(source_path) as f:
        source = f.read()

    asm_text, commands, errors = compile_source(source)
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    if output_path.endswith('.ant'):
        # Compile to fraction
        frac = encode(commands)
        with open(output_path, 'w') as f:
            f.write(f"{frac.numerator}/{frac.denominator}\n")
        print(f"Compiled → {output_path} ({len(commands)} commands)")
    else:
        # Output assembly
        with open(output_path, 'w') as f:
            f.write(asm_text + '\n')
        print(f"Compiled → {output_path} ({len(commands)} commands)")

    return 0


def cmd_debug(args):
    if not args:
        print("Error: specify source file", file=sys.stderr)
        return 1

    with open(args[0]) as f:
        source = f.read()

    asm_text, commands, errors = compile_source(source)
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    print("═══ Generated Assembly ═══")
    print(asm_text)
    print()
    print(f"═══ {len(commands)} commands ═══")
    return 0


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return 0

    mode = sys.argv[1].lower()
    args = sys.argv[2:]

    dispatch = {
        'run': cmd_run,
        'compile': cmd_compile,
        'debug': cmd_debug,
    }

    handler = dispatch.get(mode)
    if handler:
        return handler(args)
    else:
        print(USAGE)
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
