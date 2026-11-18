`timescale 1ns/1ps
//=============================================================================
// i2c_master_apb.v
// I2C master with a simple APB-style request/complete interface.
//
// The master performs a single-byte I2C read:
//   START -> {slave_addr, R/W=1} -> ACK -> 8 data bits -> ACK -> STOP
//
// Each SCL bit cell is eight clk cycles, which gives both ends of the link
// ample setup/hold margin and keeps every register in the system clock domain:
//   phase 0 : SCL falls
//   phase 1 : SDA updated while SCL is low
//   phase 2-3 : SCL low (data setup time)
//   phase 4 : SCL rises
//   phase 5-6 : SCL high (slave drives / samples)
//   phase 7 : SDA sampled while SCL is high
//=============================================================================
module i2c_master_apb (
    input  wire       clk,
    input  wire       reset,
    input  wire       apb_start,
    input  wire [6:0] apb_slave_addr,
    output reg        apb_done,
    output reg  [7:0] apb_data_out,
    output reg        scl,
    inout  wire       sda
);

    localparam [2:0] IDLE     = 3'd0,
                     START    = 3'd1,
                     ADDR     = 3'd2,
                     ADDR_ACK = 3'd3,
                     READ     = 3'd4,
                     DATA_ACK = 3'd5,
                     STOP     = 3'd6,
                     DONE     = 3'd7;

    localparam [2:0] PH_FALL   = 3'd0,
                     PH_DRIVE  = 3'd1,
                     PH_LOW2   = 3'd2,
                     PH_LOW3   = 3'd3,
                     PH_RISE   = 3'd4,
                     PH_HIGH2  = 3'd5,
                     PH_HIGH3  = 3'd6,
                     PH_SAMPLE = 3'd7;

    reg  [2:0] state;
    reg  [2:0] phase;
    reg  [3:0] bit_cnt;
    reg  [7:0] shift_reg;
    reg        sda_out;
    reg        ack_received;

    wire       sda_in;
    assign sda    = sda_out ? 1'bz : 1'b0;   // open-drain behaviour
    assign sda_in = sda;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state        <= IDLE;
            phase        <= PH_FALL;
            scl          <= 1'b1;
            sda_out      <= 1'b1;
            apb_done     <= 1'b0;
            apb_data_out <= 8'h00;
            bit_cnt      <= 4'd0;
            shift_reg    <= 8'h00;
            ack_received <= 1'b0;
        end else begin
            case (state)

                IDLE: begin
                    scl      <= 1'b1;
                    sda_out  <= 1'b1;
                    apb_done <= 1'b0;
                    if (apb_start) begin
                        state <= START;
                        phase <= PH_FALL;
                    end
                end

                // SDA falls while SCL is high -> START condition
                START: begin
                    case (phase)
                        PH_FALL: begin scl <= 1'b1; sda_out <= 1'b0; phase <= PH_DRIVE; end
                        PH_DRIVE: begin scl <= 1'b0; sda_out <= 1'b0; phase <= PH_LOW2; end
                        default: begin
                            shift_reg <= {apb_slave_addr, 1'b1};  // address + READ
                            bit_cnt   <= 4'd7;
                            state     <= ADDR;
                            phase     <= PH_FALL;
                        end
                    endcase
                end

                ADDR: begin
                    case (phase)
                        PH_FALL:   begin scl <= 1'b0; phase <= PH_DRIVE; end
                        PH_DRIVE:  begin sda_out <= shift_reg[bit_cnt]; phase <= PH_LOW2; end
                        PH_RISE:   begin scl <= 1'b1; phase <= PH_HIGH2; end
                        PH_SAMPLE: begin
                            scl <= 1'b0;
                            if (bit_cnt == 4'd0)
                                state <= ADDR_ACK;
                            else
                                bit_cnt <= bit_cnt - 4'd1;
                            phase <= PH_FALL;
                        end
                        default:   phase <= phase + 3'd1;
                    endcase
                end

                // Ninth clock: the addressed slave pulls SDA low
                ADDR_ACK: begin
                    case (phase)
                        PH_FALL:   begin scl <= 1'b0; phase <= PH_DRIVE; end
                        PH_DRIVE:  begin sda_out <= 1'b1; phase <= PH_LOW2; end   // release
                        PH_RISE:   begin scl <= 1'b1; phase <= PH_HIGH2; end
                        PH_SAMPLE: begin
                            scl          <= 1'b0;
                            ack_received <= (sda_in == 1'b0);
                            if (sda_in == 1'b0) begin
                                state   <= READ;
                                bit_cnt <= 4'd7;
                            end else begin
                                state   <= STOP;          // NACK: abort cleanly
                            end
                            phase <= PH_FALL;
                        end
                        default:   phase <= phase + 3'd1;
                    endcase
                end

                READ: begin
                    case (phase)
                        PH_FALL:   begin scl <= 1'b0; phase <= PH_DRIVE; end
                        PH_DRIVE:  begin sda_out <= 1'b1; phase <= PH_LOW2; end   // release
                        PH_RISE:   begin scl <= 1'b1; phase <= PH_HIGH2; end
                        PH_SAMPLE: begin
                            scl <= 1'b0;
                            shift_reg[bit_cnt] <= sda_in;   // MSB first
                            if (bit_cnt == 4'd0)
                                state <= DATA_ACK;
                            else
                                bit_cnt <= bit_cnt - 4'd1;
                            phase <= PH_FALL;
                        end
                        default:   phase <= phase + 3'd1;
                    endcase
                end

                // Receiver ACK for the data byte, then publish the result
                DATA_ACK: begin
                    case (phase)
                        PH_FALL:   begin scl <= 1'b0; phase <= PH_DRIVE; end
                        PH_DRIVE:  begin sda_out <= 1'b0; phase <= PH_LOW2; end   // ACK
                        PH_RISE:   begin scl <= 1'b1; phase <= PH_HIGH2; end
                        PH_SAMPLE: begin
                            apb_data_out <= shift_reg;   // all 8 bits captured
                            state        <= STOP;
                            phase        <= PH_FALL;
                        end
                        default:   phase <= phase + 3'd1;
                    endcase
                end

                // SDA rises while SCL is high -> STOP condition
                STOP: begin
                    case (phase)
                        PH_FALL:   begin scl <= 1'b0; sda_out <= 1'b0; phase <= PH_DRIVE;  end
                        PH_DRIVE:  begin scl <= 1'b0; sda_out <= 1'b0; phase <= PH_LOW2;   end
                        PH_RISE:   begin scl <= 1'b1; sda_out <= 1'b0; phase <= PH_HIGH2;  end
                        PH_SAMPLE: begin sda_out <= 1'b1; state <= DONE; phase <= PH_FALL; end
                        default:   phase <= phase + 3'd1;
                    endcase
                end

                DONE: begin
                    scl      <= 1'b1;
                    apb_done <= 1'b1;
                    state    <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
