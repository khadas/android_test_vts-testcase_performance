#!/usr/bin/env python
#
# Copyright (C) 2017 The Android Open Source Project
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

import json
import logging

from vts.runners.host import asserts
from vts.runners.host import base_test
from vts.runners.host import const
from vts.runners.host import test_runner
from vts.utils.python.controllers import android_device
from vts.utils.python.cpu import cpu_frequency_scaling


class HwBinderLatencyTest(base_test.BaseTestClass):
    """A test case for the hwbinder latency benchmarking."""

    def setUpClass(self):
        required_params = ["hidl_hal_mode"]
        self.getUserParams(required_params)
        self.dut = self.registerController(android_device)[0]
        self.dut.shell.InvokeTerminal("one")
        self._cpu_freq = cpu_frequency_scaling.CpuFrequencyScalingController(self.dut)
        self._cpu_freq.DisableCpuScaling()

    def setUp(self):
        self._cpu_freq.SkipIfThermalThrottling(retry_delay_secs=30)

    def tearDown(self):
        self._cpu_freq.SkipIfThermalThrottling()

    def tearDownClass(self):
        self._cpu_freq.EnableCpuScaling()

    def testRunBenchmark32Bit(self):
        self._uploadResult(self._runBenchmark(32), 32)

    def testRunBenchmark64Bit(self):
        self._uploadResult(self._runBenchmark(64), 64)

    def _runBenchmark(self, bits):
        """Runs the native binary and parses its result.

        Args:
            bits: integer (32 or 64), the bitness of the binary to run.

        Returns:
            dict, the benchmarking result converted from native binary's JSON
            output.
        """
        logging.info("Start %d-bit hwbinder latency test with HIDL mode=%s",
                     bits, self.hidl_hal_mode)
        binary = "/data/local/tmp/%s/libhwbinder_latency%s" % (bits, bits)
        min_cpu, max_cpu = self._cpu_freq.GetMinAndMaxCpuNo()
        iterations = 1000 // (max_cpu - min_cpu)
        results = self.dut.shell.one.Execute([
            "chmod 755 %s" % binary,
            "LD_LIBRARY_PATH=/system/lib%s:/data/local/tmp/%s/hw:"
            "/data/local/tmp/%s:$LD_LIBRARY_PATH "
            "%s -raw_data -pair %d -i %d -m %s" % (bits, bits, bits,
                binary, max_cpu - min_cpu, iterations,
                self.hidl_hal_mode.encode("utf-8"))])
        # Parses the result.
        asserts.assertEqual(len(results[const.STDOUT]), 2)
        logging.info("stderr: %s", results[const.STDERR][1])
        logging.info("stdout: %s", results[const.STDOUT][1])
        asserts.assertFalse(
            any(results[const.EXIT_CODE]),
            "testRunBenchmark%sBit failed." % (bits))
        json_result = json.loads(results[const.STDOUT][1]);
        asserts.assertTrue(json_result["inheritance"] == "PASS",
            "Scheduler does not support priority inheritance.");
        return json_result

    def _uploadResult(self, result, bits):
        """Uploads the output of benchmark program to web DB.

        Args:
            result: dict which is the benchmarking result.
            bits: integer (32 or 64).
        """
        opts = ["hidl_hal_mode=%s" % self.hidl_hal_mode.encode("utf-8")];
        min_cpu, max_cpu = self._cpu_freq.GetMinAndMaxCpuNo()
        for i in range(max_cpu - min_cpu):
            self.web.AddProfilingDataUnlabeledVector(
                "hwbinder_latency_%sbits" % bits,
                result["fifo_%d_data" % i], options=opts,
                x_axis_label="hwbinder latency",
                y_axis_label="Frequency")


if __name__ == "__main__":
    test_runner.main()
