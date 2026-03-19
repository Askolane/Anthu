# Loop Demo — noise-driven termination
#
# In Anthu, loops exit when channel capacity C ≤ 1.
# Instead of decrementing a counter to zero (like brainfuck),
# we inject noise until the signal is drowned out.
#
# Cell 0: loop counter (signal=10)
#   Each iteration injects 2 noise → C decreases
#   Loop exits when C = log₂(1 + 10/10) = 1.0
#   → 5 iterations (n goes 0 → 2 → 4 → 6 → 8 → 10)
#
# Cell 1: output accumulator
#   Each iteration amplifies by 1 → counts iterations
#   After loop: s = 5, n = 0 → clean output

# Set up counter
+10

# Loop: inject noise into counter, amplify output cell
[ !2 > + < ]

# Move to output cell, add ASCII '0' offset (48), measure
> +48 .    # s was 5 from iterations, +48 = 53 = '5'

# Newline
> +10 .
