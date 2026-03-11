<p align="center">
  <img src="anthu_logo.png" width="200"/>
</p>

# Anthu

> A fraction is a program.

**Anthu** is an esoteric programming language where the entire source code is a single rational number (`p/q`). The interpreter deconstructs it via the Euclidean algorithm and executes the result as [Brainfuck](https://esolangs.org/wiki/Brainfuck).

The name is derived from *Anthuphairesis(ἀνθυφαίρεσις)*.

---

## How It Works

1. **Compile** — A Brainfuck-like source file is compressed into one fraction using continued fractions.
2. **Run** — The fraction is decoded by repeatedly applying Euclidean division. Each quotient, taken modulo 8, maps to a command.

| Remainder | Command | Meaning        |
|-----------|---------|----------------|
| 0         | `+`     | Increment cell |
| 1         | `-`     | Decrement cell |
| 2         | `>`     | Move right     |
| 3         | `<`     | Move left      |
| 4         | `[`     | Loop start     |
| 5         | `]`     | Loop end       |
| 6         | `.`     | Output         |
| 7         | `,`     | Input          |

Any rational number is a valid Anthu program. Whether it does something meaningful is another question.

---

## Usage

### Compile
```bash
# Python
python Anthu.py compile <source.txt> <output.ant>
python Anthu.py compile <source.txt> <output.ant> -m 42

# Executable
Anthu compile <source.txt> <output.ant>
Anthu compile <source.txt> <output.ant> -m 42
```
The optional `-m` flag sets a secret multiplier for obfuscation.

### Run
```bash
# Python
python Anthu.py run <program.ant>
python Anthu.py run 355/113

# Executable
Anthu run <program.ant>
Anthu run 355/113
```

---

## Example

`examples/hello_world.ant`
```
303925317914496322502205817564846275201535643467712157141261863065221806439921522627651854132782629734120/37414916402910410930299433882971637469796074612232507916253664330404280527103649726888433831254975014403
```

```bash
Anthu run examples/hello_world.ant
# Hello, World!
```

---

## License

MIT
