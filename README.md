**This is currently a Proof of Concept. I plan to run this on the testnet environment to determine if it is more or less profitable than taking entries manually. Use at your own risk!**

# Motivation
This bot is designed to assist with trade entries using the [Kite Crypto](https://www.youtube.com/c/KiteHD) ABC trading strategy.

It sets out to achieve two problems faced when running the ABC strategy manually:
1. Formation of a new C point occurs and price retraces past the A point all while not at a computer meaning you miss the optimal trade entry
2. After getting a trade entry, your position gets stopped out but you miss out on re-entering the conditional order again for the next cross of the A point

This bot solves both these problems in the following ways:
- You see a potential upcoming ABC pattern where A & B are in place but C has not yet formed. You can submit a trade to this bot and it will enter a new conditional order for you only after the C point has been formed
    - This means you will never miss a trade entry due to not being at your computer. The bot does the monitoring for you

- The bot will then monitor the position and if it gets stopped out, it will re-enter a new conditional again to trigger a new position after the A point gets crossed again
    - This means you will never miss a good position because you got stopped out and did not get re-entered in time before price took off in the direction you anticipated it would

# Installation
Setup and installation details to follow