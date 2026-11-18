`timescale 1ns/1ps
//=============================================================================
// i2c_game_controller_slave.v
// I2C slave model of a game controller, fully synchronous to clk.
//
//  * Double-registers SCL/SDA and detects START, STOP and SCL edges.
//  * Shifts in {slave address, R/W} on the first eight SCL rising edges.
//  * Drives ACK low on the ninth clock when the address matches.
//  * Returns button_state[7:0] MSB-first on the following eight clocks.
//  * Releases SDA after the byte so the master can ACK and issue STOP.
//
// Using clk (rather than SCL) as the only clock keeps the block synthesizable
// and avoids gated clocks. It assumes the master's SCL is generated from the
// same clk, which is true for soc_top.
//=============================================================================
module i2c_game_controller_slave #(
    parameter [6:0] SLAVE_ADDR = 7'h42
) (
    input  wire       clk,
    input  wire       reset,
    input  wire       scl,
    inout  wire       sda,
    input  wire [7:0] button_state
);

    localparam [1:0] S_ADDR = 2'd0,
                     S_ACK  = 2'd1,
                     S_DATA = 2'd2,
                     S_IDLE = 2'd3;

    reg  [1:0] state;
    reg  [3:0] bit_cnt;
    reg  [7:0] addr_sr;
    reg  [3:0] addr_bits;
    reg        addr_match;
    reg  [7:0] data_out;
    reg        sda_drive;
    reg        sda_reg;

    // Bus synchronisers / edge history
    reg  [2:0] scl_sync;
    reg  [2:0] sda_sync;
    reg        scl_q;
    reg        sda_q;

    wire scl_rise  =  scl_sync[1] && !scl_q;
    wire scl_fall  = !scl_sync[1] &&  scl_q;
    wire start_det =  scl_sync[1] &&  sda_q && !sda_sync[1];
    wire stop_det  =  scl_sync[1] && !sda_q &&  sda_sync[1];

    assign sda = sda_drive ? sda_reg : 1'bz;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state      <= S_IDLE;
            addr_sr    <= 8'h00;
            addr_bits  <= 4'd0;
            addr_match <= 1'b0;
            sda_drive  <= 1'b0;
            sda_reg    <= 1'b1;
            data_out   <= 8'h00;
            bit_cnt    <= 4'd7;
            scl_sync   <= 3'b111;
            sda_sync   <= 3'b111;
            scl_q      <= 1'b1;
            sda_q      <= 1'b1;
        end else begin
            // Two-stage synchronisers plus one-cycle history
            scl_sync <= {scl_sync[1:0], scl};
            sda_sync <= {sda_sync[1:0], sda};
            scl_q    <= scl_sync[1];
            sda_q    <= sda_sync[1];

            if (start_det) begin
                //---------------- START / repeated START ----------------
                state      <= S_ADDR;
                addr_sr    <= 8'h00;
                addr_bits  <= 4'd0;
                addr_match <= 1'b0;
                sda_drive  <= 1'b0;
                sda_reg    <= 1'b1;
                bit_cnt    <= 4'd7;
                data_out   <= button_state;          // latch controller state
            end else if (scl_rise) begin
                //---------------- SCL rising edge ----------------
                case (state)
                    S_ADDR: begin
                        addr_sr   <= {addr_sr[6:0], sda_sync[1]};
                        addr_bits <= addr_bits + 4'd1;
                        if (addr_bits == 4'd7) begin
                            addr_match <= ({addr_sr[6:0], sda_sync[1]} == {SLAVE_ADDR, 1'b1});
                            state      <= S_ACK;
                        end
                    end

                    S_ACK: begin
                        if (addr_match) begin
                            state   <= S_DATA;
                            bit_cnt <= 4'd7;
                        end else begin
                            state     <= S_IDLE;
                            addr_bits <= 4'd0;
                        end
                    end

                    S_DATA: begin
                        if (bit_cnt == 4'd0) begin
                            state     <= S_IDLE;
                            addr_bits <= 4'd0;
                        end else begin
                            bit_cnt <= bit_cnt - 4'd1;
                        end
                    end

                    default: state <= S_IDLE;
                endcase

            end else if (scl_fall) begin
                //---------------- SCL falling edge ----------------
                case (state)
                    S_ACK: begin
                        sda_drive <= 1'b1;
                        sda_reg   <= addr_match ? 1'b0 : 1'b1;   // ACK / NACK
                    end

                    S_DATA: begin
                        sda_drive <= 1'b1;
                        sda_reg   <= data_out[bit_cnt];          // MSB first
                    end

                    default: begin
                        sda_drive <= 1'b0;
                        sda_reg   <= 1'b1;
                    end
                endcase

            end else if (stop_det) begin
                //---------------- STOP condition ----------------
                state     <= S_IDLE;
                sda_drive <= 1'b0;
                sda_reg   <= 1'b1;
                addr_bits <= 4'd0;
            end
        end
    end

endmodule
