#!/usr/bin/env python3.4
#
# Copyright (C) 2016 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging

from vts.runners.host import asserts
from vts.runners.host import base_test_with_webdb
from vts.runners.host import test_runner
from vts.utils.python.controllers import android_device
from vts.runners.host import const


class HwBinderPerformanceTest(base_test_with_webdb.BaseTestWithWebDbClass):
    """A test case for the HWBinder performance benchmarking."""

    DELIMITER = "\033[m\033[0;33m"
    SCREEN_COMMANDS = ["\x1b[0;32m", "\x1b[m\x1b[0;36m", "\x1b[m", "\x1b[m"]
    THRESHOLD = {
        32: {
            "BM_sendVec/64": 100000,
            "BM_sendVec/128": 100000,
            "BM_sendVec/256": 100000,
            "BM_sendVec/512": 100000,
            "BM_sendVec/1024": 100000,
            "BM_sendVec/2k": 100000,
            "BM_sendVec/4k": 100000,
            "BM_sendVec/8k": 110000,
            "BM_sendVec/16k": 120000,
            "BM_sendVec/32k": 140000,
            "BM_sendVec/64k": 170000,
        },
        64: {
            "BM_sendVec/64": 100000,
            "BM_sendVec/128": 100000,
            "BM_sendVec/256": 100000,
            "BM_sendVec/512": 100000,
            "BM_sendVec/1024": 100000,
            "BM_sendVec/2k": 100000,
            "BM_sendVec/4k": 100000,
            "BM_sendVec/8k": 110000,
            "BM_sendVec/16k": 120000,
            "BM_sendVec/32k": 150000,
            "BM_sendVec/64k": 200000,
        }
    }
    LABEL_PREFIX = "BM_sendVec/"

    def setUpClass(self):
        required_params = ["hidl_hal_mode"]
        self.getUserParams(required_params)
        self.dut = self.registerController(android_device)[0]
        self.dut.shell.InvokeTerminal("one")
        self.DisableCpuScaling()

    def tearDownClass(self):
        self.EnableCpuScaling()

    def ChangeCpuGoverner(self, mode):
        """Changes the cpu governer mode of all the cpus on the device.

        Args:
            mode:expected cpu governer mode. e.g performan/interactive.
        """
        results = self.dut.shell.one.Execute(
            "cat /sys/devices/system/cpu/possible")
        asserts.assertEqual(len(results[const.STDOUT]), 1)
        stdout_lines = results[const.STDOUT][0].split("\n")
        (low, high) = stdout_lines[0].split('-')
        logging.info("possible cpus: %s : %s" % (low, high))

        for cpu_no in range(int(low), int(high)):
          self.dut.shell.one.Execute(
             "echo %s > /sys/devices/system/cpu/cpu%s/"
             "cpufreq/scaling_governor" % (mode, cpu_no))

    def DisableCpuScaling(self):
        """Disable CPU frequency scaling on the device."""
        self.ChangeCpuGoverner("performance")

    def EnableCpuScaling(self):
        """Enable CPU frequency scaling on the device."""
        self.ChangeCpuGoverner("interactive")

    def testRunBenchmark32Bit(self):
        """A testcase which runs the 32-bit benchmark."""
        self.RunBenchmark(32)

    def testRunBenchmark64Bit(self):
        """A testcase which runs the 64-bit benchmark."""
        self.RunBenchmark(64)

    def RunBenchmark(self, bits):
        """Runs the native binary and parses its result.

        Args:
            bits: integer (32 or 64), the number of bits in a word chosen
                  at the compile time (e.g., 32- vs. 64-bit library).
        """
        # Runs the benchmark.
        logging.info("Start to run the benchmark with HIDL mode %s (%s bit mode)",
                     self.hidl_hal_mode, bits)
        binary = "/data/local/tmp/%s/libhwbinder_benchmark%s" % (bits, bits)

        results = self.dut.shell.one.Execute(
            ["chmod 755 %s" % binary,
             "LD_LIBRARY_PATH=/data/local/tmp/%s/hw:"
             "/data/local/tmp/%s:"
             "$LD_LIBRARY_PATH %s -m %s" % (bits, bits, binary, self.hidl_hal_mode.encode("utf-8"))])

        # Parses the result.
        asserts.assertEqual(len(results[const.STDOUT]), 2)
        logging.info("stderr: %s", results[const.STDERR][1])
        stdout_lines = results[const.STDOUT][1].split("\n")
        logging.info("stdout: %s", stdout_lines)
        label_result = []
        value_result = []
        for line in stdout_lines:
            if self.DELIMITER in line:
                tokens = []
                for line_original in line.split(self.DELIMITER):
                    line_original = line_original.strip()
                    for command in self.SCREEN_COMMANDS:
                        if command in line_original:
                            line_original = line_original.replace(command, "")
                    tokens.append(line_original)
                benchmark_name = tokens[0]
                time_in_ns = tokens[1].split()[0]
                logging.info(benchmark_name)
                logging.info(time_in_ns)
                label_result.append(benchmark_name.replace(self.LABEL_PREFIX, ""))
                value_result.append(int(time_in_ns))

        logging.info("result label for %sbits: %s", bits, label_result)
        logging.info("result value for %sbits: %s", bits, value_result)
        # To upload to the web DB.
        self.AddProfilingDataLabeledVector(
            "hwbinder_vector_roundtrip_latency_benchmark_%sbits" % bits,
            label_result, value_result, x_axis_label="Message Size (Bytes)",
            y_axis_label="Roundtrip HwBinder RPC Latency (naonseconds)")

        # Assertions to check the performance requirements
        for label, value in zip(label_result, value_result):
            if label in self.THRESHOLD[bits]:
                asserts.assertLess(
                    value,
                    self.THRESHOLD[bits][label],
                    "%s ns for %s is longer than the threshold %s ns" % (
                        value, label, self.THRESHOLD[bits][label]))

if __name__ == "__main__":
    test_runner.main()
