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

    reg [2:0] sclk_sync;
    reg [2:0] ncs_sync;
    reg [1:0] copi_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync <= 3'b000;
            ncs_sync  <= 3'b111;
            copi_sync <= 2'b00;
        end else begin
            sclk_sync <= {sclk_sync[1:0], sclk};
            ncs_sync  <= {ncs_sync[1:0], ncs};
            copi_sync <= {copi_sync[0], copi};
        end
    end

    wire ncs_clean   = ncs_sync[2];
    wire copi_clean  = copi_sync[1];
    wire sclk_rising = sclk_sync[2] && !sclk_sync[1];
    wire ncs_falling = !ncs_sync[2] && ncs_sync[1];

    reg [15:0] shift_reg;
    reg [4:0]  bit_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg       <= 16'h0000;
            bit_count       <= 5'd0;
            en_reg_out_7_0  <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0  <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle  <= 8'h00;
        end else if (ncs_falling) begin
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
                    default: ;
                endcase
            end
        end
    end

endmodule
