`default_nettype none

module spi_peripheral (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sclk,
    input  wire       ncs,
    input  wire       copi,
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);

    // 2-stage CDC synchronizers
    reg [1:0] sclk_sync;
    reg [1:0] ncs_sync;
    reg [1:0] copi_sync;

    // one-cycle-delayed copies of the settled signals, for edge detection
    reg sclk_prev;
    reg ncs_prev;

    wire sclk_clean = sclk_sync[1];
    wire ncs_clean  = ncs_sync[1];
    wire copi_clean = copi_sync[1];

    wire sclk_rising = sclk_clean && !sclk_prev;
    wire ncs_falling = !ncs_clean && ncs_prev;

    reg [15:0] shift_reg;
    reg [4:0]  bit_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync       <= 2'b00;
            ncs_sync        <= 2'b11;
            copi_sync       <= 2'b00;
            sclk_prev       <= 1'b0;
            ncs_prev        <= 1'b1;
            shift_reg       <= 16'h0000;
            bit_count       <= 5'd0;
            en_reg_out_7_0  <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0  <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle  <= 8'h00;
        end else begin
            // advance the synchronizers every cycle
            sclk_sync <= {sclk_sync[0], sclk};
            ncs_sync  <= {ncs_sync[0], ncs};
            copi_sync <= {copi_sync[0], copi};
            // remember this cycle's settled level, to detect next cycle's edge
            sclk_prev <= sclk_clean;
            ncs_prev  <= ncs_clean;

            if (ncs_falling) begin
                bit_count <= 5'd0;
            end else if (!ncs_clean && sclk_rising) begin
                shift_reg <= {shift_reg[14:0], copi_clean};
                bit_count <= bit_count + 1'b1;
            end else if (bit_count == 5'd16) begin
                bit_count <= 5'd0;
                if (shift_reg[15]) begin
                    case (shift_reg[14:8])
                        7'h00: en_reg_out_7_0  <= shift_reg[7:0];
                        7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                        7'h02: en_reg_pwm_7_0  <= shift_reg[7:0];
                        7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                        7'h04: pwm_duty_cycle  <= shift_reg[7:0];
                        default: ; // invalid address - ignore
                    endcase
                end
            end
        end
    end

endmodule
