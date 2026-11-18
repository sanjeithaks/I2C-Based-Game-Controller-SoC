`timescale 1ns/1ps
module tb_trace;
    reg clk=0, reset=1, apb_start=0;
    reg [6:0] slave_addr = 7'b1000010;
    reg [7:0] controller_buttons = 8'b10101100;
    wire scl, sda;
    wire [7:0] button_status;
    soc_top dut (.clk(clk),.reset(reset),.apb_start(apb_start),.slave_addr(slave_addr),
        .controller_buttons(controller_buttons),.button_status(button_status),.scl(scl),.sda(sda));
    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (dut.master.state == 3) begin
            $display("t=%0t READ scl_old=%b bit_cnt=%0d sda=%b sda_out=%b shift=%b",
                     $time, scl, dut.master.bit_cnt, sda, dut.master.sda_out, dut.master.shift_reg);
        end
        if (dut.master.state == 2) begin
            $display("t=%0t ADDR scl_old=%b bit_cnt=%0d sda=%b sda_out=%b shift=%b",
                     $time, scl, dut.master.bit_cnt, sda, dut.master.sda_out, dut.master.shift_reg);
        end
    end
    initial begin
        #22 reset=0; #20 apb_start=1; #10 apb_start=0; #900 $finish;
    end
endmodule
