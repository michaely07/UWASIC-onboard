<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

An SPI peripheral module receives register writes over SPI and uses them to control a PWM peripheral.

## How to test

- `test_pwm_freq` enables output + PWM on one bit at 50% duty cycle and measures the period between
  consecutive high levels, checking the frequency lands within ~1% of 3 kHz.
- `test_pwm_duty` checks 0%, 50%, and 100% duty cycle settings, including that 0%/100% hold the output
  constant rather than toggling.
## External hardware

None
