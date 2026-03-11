#!/usr/bin/env python3
import sys
import os
import argparse
from fractions import Fraction

MAP_TO_CMD = {0: '+', 1: '-', 2: '>', 3: '<', 4: '[', 5: ']', 6: '.', 7: ','}
CMD_TO_MAP = {v: k for k, v in MAP_TO_CMD.items()}

class Weaver:
    @staticmethod
    def compile(source_code, secret_multiplier=1):
        clean_code = [char for char in source_code if char in CMD_TO_MAP]
        if not clean_code:
            raise ValueError("No valid Brainfuck commands found.")

        offset = 8 * secret_multiplier
        int_array = [CMD_TO_MAP[char] + offset for char in clean_code]

        current_fraction = Fraction(int_array[-1], 1)
        for num in reversed(int_array[:-1]):
            current_fraction = num + Fraction(1, current_fraction)

        return current_fraction

class AnthuVM:
    def __init__(self):
        self.tape = [0] * 30000
        self.ptr = 0

    def decode_fraction(self, frac_str):
        try:
            frac = Fraction(frac_str)
        except ValueError:
            raise ValueError("Invalid fraction or rational number.")

        num = abs(frac.numerator)
        den = abs(frac.denominator)

        quotients = []
        while den != 0:
            q = num // den
            r = num % den
            quotients.append(q)
            num = den
            den = r

        return "".join([MAP_TO_CMD[q % 8] for q in quotients])

    def execute(self, code):
        pc = 0
        loop_map = {}
        loop_stack = []

        for i, char in enumerate(code):
            if char == '[':
                loop_stack.append(i)
            elif char == ']':
                if not loop_stack:
                    raise SyntaxError("Unmatched ']'")
                start = loop_stack.pop()
                loop_map[start] = i
                loop_map[i] = start
        if loop_stack:
            raise SyntaxError("Unmatched '['")

        while pc < len(code):
            cmd = code[pc]
            if cmd == '>':
                self.ptr = (self.ptr + 1) % len(self.tape)
            elif cmd == '<':
                self.ptr = (self.ptr - 1) % len(self.tape)
            elif cmd == '+':
                self.tape[self.ptr] = (self.tape[self.ptr] + 1) % 256
            elif cmd == '-':
                self.tape[self.ptr] = (self.tape[self.ptr] - 1) % 256
            elif cmd == '.':
                sys.stdout.write(chr(self.tape[self.ptr]))
                sys.stdout.flush()
            elif cmd == ',':
                char = sys.stdin.read(1)
                if char:
                    self.tape[self.ptr] = ord(char)
            elif cmd == '[':
                if self.tape[self.ptr] == 0:
                    pc = loop_map[pc]
            elif cmd == ']':
                if self.tape[self.ptr] != 0:
                    pc = loop_map[pc]
            pc += 1

def main():
    parser = argparse.ArgumentParser(description="Anthu: The Fraction-Oriented Esoteric Language")
    subparsers = parser.add_subparsers(dest="command", help="Command to run (compile/run)")

    compile_parser = subparsers.add_parser("compile", help="Compile Brainfuck to .ant fraction")
    compile_parser.add_argument("source", help="Source code file")
    compile_parser.add_argument("output", help="Output .ant file")
    compile_parser.add_argument("-m", "--multiplier", type=int, default=1, help="Obfuscation multiplier")

    run_parser = subparsers.add_parser("run", help="Run an .ant file or fraction string")
    run_parser.add_argument("target", help=".ant file or direct fraction (e.g., 355/113)")

    args = parser.parse_args()

    if args.command == "compile":
        try:
            with open(args.source, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            result_fraction = Weaver.compile(source_code, args.multiplier)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(f"{result_fraction.numerator}/{result_fraction.denominator}")
                
            print(f"[*] Compiled effectively: {args.output}")
        except Exception as e:
            print(f"[!] Error: {e}")

    elif args.command == "run":
        vm = AnthuVM()
        try:
            if os.path.isfile(args.target):
                with open(args.target, 'r', encoding='utf-8') as f:
                    frac_str = f.read().strip()
            else:
                frac_str = args.target
                
            decoded_code = vm.decode_fraction(frac_str)

            if decoded_code:
                vm.execute(decoded_code)
                print()
            
        except Exception as e:
            print(f"[!] Error: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()