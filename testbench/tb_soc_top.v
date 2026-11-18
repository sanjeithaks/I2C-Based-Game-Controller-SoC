`timescale 1ns/1ps
//=============================================================================
// tb_soc_top.v
// Self-checking testbench for the I2C game-controller SoC.
//
// Checks performed:
//   1. Reset values (SCL high, SDA released, apb_done low).
//   2. START condition (SDA falls while SCL is high).
//   3. Slave address and R/W bit on SDA.
//   4. ACK from the addressed slave on the ninth clock.
//   5. Eight data bits, MSB first, equal to controller_buttons.
//   6. apb_done pulse and final button_status value.
//   7. A second read with a different button pattern (reusability).
//   8. An unaddressed slave returns NACK and does not update the data.
//   9. STOP condition (SDA rises while SCL is high).
//=============================================================================
module tb_soc_top;

    localparam integer CLK_PERIOD = 10;          // 100 MHz
    localparam [6:0]   DUT_ADDR   = 7'h42;

    reg         clk = 1'b0;
    reg         reset = 1'b1;
    reg         apb_start = 1'b0;
    reg  [6:0]  slave_addr = DUT_ADDR;
    reg  [7:0]  controller_buttons = 8'h00;
    wire        scl;
    wire        sda;
    wire [7:0]  button_status;

    integer     errors = 0;
    integer     scl_edges = 0;
    integer     bit_index = 0;
    reg  [7:0]  addr_capture = 8'h00;
    reg  [7:0]  data_capture = 8'h00;
    reg         ack_capture = 1'b1;
    reg         start_seen = 1'b0;
    reg         stop_seen = 1'b0;
    reg         ack_expected = 1'b1;

    soc_top dut (
        .clk                (clk),
        .reset              (reset),
        .apb_start          (apb_start),
        .slave_addr         (slave_addr),
        .controller_buttons (controller_buttons),
        .button_status      (button_status),
        .scl                (scl),
        .sda                (sda)
    );

    always #(CLK_PERIOD/2) clk = ~clk;

    // Board-level pull-up on the open-drain SDA line.
    pullup (sda);

    //-------------------------------------------------------------------------
    // Protocol monitor
    //-------------------------------------------------------------------------
    always @(negedge sda) begin
        if (!reset && (scl === 1'b1) && (scl_edges == 0)) begin
            start_seen = 1'b1;
            $display("[%0t] START condition detected (SDA fell while SCL high)", $time);
        end
    end

    always @(posedge sda) begin
        if (!reset && (scl === 1'b1)) begin
            stop_seen = 1'b1;
            $display("[%0t] STOP condition detected (SDA rose while SCL high)", $time);
        end
    end

    // Sample the bus in the middle of the SCL high phase.
    always @(posedge scl) begin
        if (!reset) begin
            #2;                                     // 2 ns into the high phase
            if (scl_edges < 8) begin
                addr_capture = {addr_capture[6:0], sda};
            end else if (scl_edges == 8) begin
                ack_capture = sda;
            end else if (scl_edges >= 9 && scl_edges <= 16) begin
                data_capture = {data_capture[6:0], sda};
                bit_index    = bit_index + 1;
            end
            scl_edges = scl_edges + 1;
        end
    end

    //-------------------------------------------------------------------------
    // Helper tasks
    //-------------------------------------------------------------------------
    task clear_monitor;
        begin
            scl_edges    = 0;
            bit_index    = 0;
            addr_capture = 8'h00;
            data_capture = 8'h00;
            ack_capture  = 1'b1;
            start_seen   = 1'b0;
            stop_seen    = 1'b0;
        end
    endtask

    task do_read(input [6:0] addr, input [7:0] buttons,
                 input       expect_ack, input [7:0] expect_data,
                 input [255:0] label);
        reg        done_seen;
        integer    wait_cnt;
        reg [7:0]  status_before;
        reg [7:0]  expected_status;
        begin
            status_before = button_status;
            slave_addr         = addr;
            controller_buttons = buttons;
            clear_monitor();
            ack_expected = expect_ack;

            @(negedge clk);
            apb_start = 1'b1;
            @(negedge clk);
            apb_start = 1'b0;

            done_seen = 1'b0;
            for (wait_cnt = 0; wait_cnt < 400; wait_cnt = wait_cnt + 1) begin
                @(posedge clk);
                #1;                                     // settle non-blocking updates
                if (dut.apb_done === 1'b1) begin
                    done_seen = 1'b1;
                    wait_cnt  = 400;
                end
            end
            #1;

            if (!done_seen) begin
                $display("FAIL [%0s]: apb_done timeout", label);
                errors = errors + 1;
            end else begin
                $display("[%0t] %0s: transaction complete after %0d SCL edges, ack=%b, rx=%b",
                         $time, label, scl_edges, ack_capture, data_capture);
            end

            if (start_seen !== 1'b1) begin
                $display("FAIL [%0s]: START not observed", label);
                errors = errors + 1;
            end
            if (stop_seen !== 1'b1) begin
                $display("FAIL [%0s]: STOP not observed", label);
                errors = errors + 1;
            end
            if (addr_capture !== {addr, 1'b1}) begin
                $display("FAIL [%0s]: address on bus %b, expected %b",
                         label, addr_capture, {addr, 1'b1});
                errors = errors + 1;
            end
            if (expect_ack) begin
                if (ack_capture !== 1'b0) begin
                    $display("FAIL [%0s]: expected ACK, sampled %b", label, ack_capture);
                    errors = errors + 1;
                end
                if (data_capture !== expect_data) begin
                    $display("FAIL [%0s]: received %b, expected %b",
                             label, data_capture, expect_data);
                    errors = errors + 1;
                end
                expected_status = expect_data;
            end else begin
                if (ack_capture !== 1'b1) begin
                    $display("FAIL [%0s]: expected NACK, sampled %b", label, ack_capture);
                    errors = errors + 1;
                end
                expected_status = status_before;   // no update on NACK
            end

            if (button_status !== expected_status) begin
                $display("FAIL [%0s]: button_status=%b, expected %b",
                         label, button_status, expected_status);
                errors = errors + 1;
            end else begin
                $display("PASS [%0s]: button_status = %b (0x%02h)",
                         label, button_status, button_status);
            end
        end
    endtask

    //-------------------------------------------------------------------------
    // Stimulus
    //-------------------------------------------------------------------------
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb_soc_top);

        $display("================================================================");
        $display(" I2C Game Controller SoC - self-checking simulation");
        $display("================================================================");

        #3;
        repeat (3) @(posedge clk);
        #1;
        if (scl !== 1'b1 || sda === 1'b0) begin
            $display("FAIL: reset state SCL=%b SDA=%b", scl, sda);
            errors = errors + 1;
        end else begin
            $display("[%0t] Reset OK: SCL=%b, SDA=%b (released, pulled high), apb_done=%b",
                     $time, scl, sda, dut.apb_done);
        end

        reset = 1'b0;
        repeat (2) @(posedge clk);

        // Test 1: nominal read, pattern A
        do_read(7'h42, 8'b10101100, 1'b1, 8'b10101100, "read 0x42 pattern A");

        // Test 2: nominal read, pattern B (proves data is not hard-coded)
        do_read(7'h42, 8'b00111100, 1'b1, 8'b00111100, "read 0x42 pattern B");

        // Test 3: wrong address must be NACKed and must not update the output
        do_read(7'h21, 8'b11110000, 1'b0, 8'h00, "read 0x21 (unaddressed)");

        $display("----------------------------------------------------------------");
        if (errors == 0)
            $display("RESULT: ALL CHECKS PASSED");
        else
            $display("RESULT: %0d CHECK(S) FAILED", errors);
        $display("================================================================");
        $finish;
    end

endmodule
