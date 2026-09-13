# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import Edge
from cocotb.triggers import ClockCycles
from cocotb.triggers import Timer
from cocotb.triggers import First
from cocotb.types import Logic
from cocotb.types import LogicArray

# PWM peripheral divides the 10 MHz clk by (12+1)*256 = 3328,
# giving a real period of ~332800 ns
PWM_EDGE_TIMEOUT_NS = 400_000

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data

    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000)

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

#helper functions
async def reset_dut(dut):
    """Start reset with SPI idle."""
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)  # ncs=1, bit=0, sclk=0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def wait_for_uo0_level(dut, expected_level, timeout_ns=PWM_EDGE_TIMEOUT_NS):
    """
    Block until uo_out[0] is observed at expected_level. Raises if no edge
    occurs for a full timeout window.
    """
    while True:
        result = await First(Edge(dut.uo_out), Timer(timeout_ns, units="ns"))
        if isinstance(result, Timer):
            raise TimeoutError(
                f"uo_out[0] never reached level {expected_level} within {timeout_ns} ns"
            )
        if (int(dut.uo_out.value) & 0x01) == expected_level:
            return


async def measure_pwm_period_ns(dut):
    """Measure one PWM period as the time between two consecutive high levels."""
    await wait_for_uo0_level(dut, 1)
    t1 = cocotb.utils.get_sim_time(units="ns")
    await wait_for_uo0_level(dut, 1)
    t2 = cocotb.utils.get_sim_time(units="ns")
    return t2 - t1


async def measure_duty_cycle_pct(dut):
    """
    Measure duty cycle % of uo_out[0] via rise -> fall -> rise timing."""
    await wait_for_uo0_level(dut, 1)
    t_rise1 = cocotb.utils.get_sim_time(units="ns")
    await wait_for_uo0_level(dut, 0)
    t_fall = cocotb.utils.get_sim_time(units="ns")
    await wait_for_uo0_level(dut, 1)
    t_rise2 = cocotb.utils.get_sim_time(units="ns")

    period = t_rise2 - t_rise1
    high_time = t_fall - t_rise1
    return (high_time / period) * 100.0


@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM Frequency test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    dut._log.info("Enable output + PWM on uo_out[0], 50% duty cycle")
    await send_spi_transaction(dut, 1, 0x00, 0x01)  # en_reg_out_7_0[0] = 1
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # en_reg_pwm_7_0[0] = 1
    await send_spi_transaction(dut, 1, 0x04, 0x80)  # 50% duty cycle

    period_ns = await measure_pwm_period_ns(dut)
    freq_hz = 1e9 / period_ns
    dut._log.info(f"Measured period={period_ns} ns, frequency={freq_hz:.2f} Hz")

    assert 2970 <= freq_hz <= 3030, \
        f"Frequency {freq_hz:.2f} Hz outside +/-1% of 3000 Hz"

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    dut._log.info("Enable output + PWM on uo_out[0]")
    await send_spi_transaction(dut, 1, 0x00, 0x01)  # en_reg_out_7_0[0] = 1
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # en_reg_pwm_7_0[0] = 1

    dut._log.info("Check 50% duty cycle")
    await send_spi_transaction(dut, 1, 0x04, 0x80)
    measured_pct = await measure_duty_cycle_pct(dut)
    dut._log.info(f"duty_reg=0x80: expected 50.00%, measured {measured_pct:.2f}%")
    assert abs(measured_pct - 50.0) <= 1.0, (
        f"Duty cycle out of +/-1% tolerance for reg=0x80: expected 50.00%, got {measured_pct:.2f}%"
    )

    dut._log.info("Check 0% duty cycle forces output constant low")
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    for _ in range(5):
        await ClockCycles(dut.clk, 1000)
        assert dut.uo_out[0].value == 0, "Expected PWM output to stay low for duty cycle 0x00"

    dut._log.info("Check 100% duty cycle forces output constant high")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    for _ in range(5):
        await ClockCycles(dut.clk, 1000)
        assert dut.uo_out[0].value == 1, "Expected PWM output to stay high for duty cycle 0xFF"

    dut._log.info("PWM Duty Cycle test completed successfully")
