# Noise Demo — information decay in action
#
# Same signal (72 = 'H'), increasing noise levels.
# Output = min(s, (s+n)//n) — integer channel capacity.
#
# Cell 0: (72,  0)  → perfect    → output 72 = 'H'
# Cell 1: (72,  1)  → (73//1)=73 → output 72 = 'H'  (still clean)
# Cell 2: (72,  8)  → (80//8)=10 → output 10         (degraded)
# Cell 3: (72, 72)  → (144//72)=2 → output 2          (nearly destroyed)
# Cell 4: (72,200)  → (272//200)=1 → output 1          (destroyed)

+72 .             # Clean: 'H'
> +72 ! .         # 1 noise: still 'H'
> +72 !8 .        # 8 noise: degraded
> +72 !72 .       # Equal noise: barely readable
> +72 !200 .      # Overwhelmed: destroyed
