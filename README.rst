Tutorial - Fixing ROS 2 ASAN/TSAN Issues
========================================

Note: this tutorial is mainly focused around ASAN but TSAN issues can be
handled in similar way.

Pre-Requisites
--------------

-  Install all ROS 2 build dependencies by following the `official instructions
   <https://index.ros.org/doc/ros2/Installation/Linux-Development-Setup/>`__.
-  Install and enable Colcon mixin package:

.. code:: bash

    sudo apt-get install python3-colcon-mixin
    colcon mixin add default https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml
    colcon mixin update default

Mixins are “configuration profiles” which can be used to compile ROS 2
with additional flags more easily. They are stored locally in
``~/.colcon``. For instance, you can see the `asan mixin configuration
file
here <https://github.com/colcon/colcon-mixin-repository/blob/master/asan.mixin>`__.

- Install colcon-sanitizer-reports (Recommended):

.. code:: bash

    git clone https://github.com/colcon/colcon-sanitizer-reports.git
    cd colcon-sanitizer-reports
    sudo python3 setup.py install

The colcon-sanitizer-reports is a plugin for ``colcon test`` that parses
sanitizer issues from stdout/stderr, deduplicates the issues, and outputs them
to a CSV. The CSV provides a much easier starting point for choosing sanitizer
issues to tackle and should contain enough information to debug the issue
completely.

-  Setup ``ccache`` to speed-up development:

.. code:: bash

    sudo apt install -y ccache
    ccache -M 20G # increase cache size
    # Add the following to your .bashrc or .zshrc file and restart your terminal:
    export CC=/usr/lib/ccache/gcc
    export CXX=/usr/lib/ccache/g++

-  Create a ROS 2 workspace for ASAN related tasks (do not compile yet!)

.. code:: bash

    cd ~/ros2_asan_ws
    wget https://raw.githubusercontent.com/ros2/ros2/master/ros2.repos
    vcs-import src < ros2.repos

Skipping unnecessary packages (Recommended)
-------------------------------------------

Unless you are specifically testing these packages, you may ignore them to save time:

.. code:: bash

    touch src/ros2/common_interfaces/actionlib_msgs/COLCON_IGNORE
    touch src/ros2/common_interfaces/common_interfaces/COLCON_IGNORE
    touch src/ros2/rosidl_typesupport_opensplice/opensplice_cmake_module/COLCON_IGNORE
    touch src/ros2/rmw_fastrtps/rmw_fastrtps_dynamic_cpp/COLCON_IGNORE
    touch src/ros2/rmw_opensplice/rmw_opensplice_cpp/COLCON_IGNORE
    touch src/ros2/ros1_bridge/COLCON_IGNORE
    touch src/ros2/rosidl_typesupport_opensplice/rosidl_typesupport_opensplice_c/COLCON_IGNORE
    touch src/ros2/rosidl_typesupport_opensplice/rosidl_typesupport_opensplice_cpp/COLCON_IGNORE
    touch src/ros2/common_interfaces/shape_msgs/COLCON_IGNORE
    touch src/ros2/common_interfaces/stereo_msgs/COLCON_IGNORE
    touch src/ros2/common_interfaces/trajectory_msgs/COLCON_IGNORE

Compiling the code and running the tests
----------------------------------------

-  First, compile all packages:

.. code:: bash

    cd ~/ros2_asan_ws  # you will need to be exactly in this directory
    # Those flags are similar to what the nightly job uses.
    colcon build --build-base=build-asan --install-base=install-asan \
        --cmake-args -DOSRF_TESTING_TOOLS_CPP_DISABLE_MEMORY_TOOLS=ON \
                     -DINSTALL_EXAMPLES=OFF -DSECURITY=ON --no-warn-unused-cli \
                     -DCMAKE_BUILD_TYPE=Debug \
        --mixin asan-gcc \
        --packages-up-to test_communication \
        --symlink-install

.. code:: bash

    # Equivalent command for tsan:
    # You can either use different workspaces or the same one.
    colcon build --build-base=build-tsan --install-base=install-tsan \
        --cmake-args -DOSRF_TESTING_TOOLS_CPP_DISABLE_MEMORY_TOOLS=ON \
                     -DINSTALL_EXAMPLES=OFF -DSECURITY=ON --no-warn-unused-cli \
                     -DCMAKE_BUILD_TYPE=Debug \
        --mixin tsan \
        --packages-up-to test_communication \
        --symlink-install

⚠️ **IMPORTANT:** Do not forget to pass ``-DCMAKE_BUILD_TYPE=Debug`` to
ensure that debugging symbols are generated. This allows ASAN/MSAN to
report files and line numbers in backtraces.

Once the compilation is finished, colcon will report that all packages
have been compiled but some had “stderr output”. This is fine.

-  To run the tests for ASan:

.. code:: bash

    cd ~/ros2_asan_ws  # you will need to be exactly in this directory
    colcon test --build-base=build-asan --install-base=install-asan \
        --event-handlers sanitizer_report+ --packages-up-to test_communication

-  To run tests for TSan

.. code:: bash

    cd ~/ros2_asan_ws  # you will need to be exactly in this directory
    colcon test --build-base=build-tsan --install-base=install-tsan \
        --event-handlers sanitizer_report+ --packages-up-to test_communication

Omit the ``--event-handlers`` flag if you did not install
colcon-sanitizer-reports.

Some tests may fail, this is OK. Once done, you can look at the test
logs or sanitizer_report.csv. Examples from tests logs:

.. code:: bash

    cd ~/ros2_asan_ws  # you will need to be exactly in this directory
    cd log/latest_test
    # Displays three lines after the beginning of a ASAN reported issue.
    grep -R '==.*==ERROR: .*Sanitizer' -A 3
    [..]
    --
    rcpputils/stdout_stderr.log:1: ==32481==ERROR: LeakSanitizer: detected memory leaks
    rcpputils/stdout_stderr.log-1:
    rcpputils/stdout_stderr.log-1: Direct leak of 4 byte(s) in 1 object(s) allocated from:
    rcpputils/stdout_stderr.log-1:     #0 0x7f7d99dac458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
    --
    rcpputils/stdout.log:1: ==32481==ERROR: LeakSanitizer: detected memory leaks
    rcpputils/stdout.log-1:
    rcpputils/stdout.log-1: Direct leak of 4 byte(s) in 1 object(s) allocated from:
    rcpputils/stdout.log-1:     #0 0x7f7d99dac458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
    --
    rcpputils/streams.log:1: ==32481==ERROR: LeakSanitizer: detected memory leaks
    rcpputils/streams.log-1:
    rcpputils/streams.log-1: Direct leak of 4 byte(s) in 1 object(s) allocated from:
    rcpputils/streams.log-1:     #0 0x7f7d99dac458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)

*Note*: if you re-run colcon test, latest\_test symbolic link will be
updated and will point to a different category. Run ``ls -l log`` to
identify which log directory you have been looking at (e.g.
``latest_test → test_2019-04-05_18-03-24``) and make a note of the
string you are seeing (``test_2019-04-05_18-03-24``) in my case. This
will ensure you don't forget which colcon test run contain the logs
you've been analyzing.

Choosing a package to work on
-----------------------------

When we will have a stack-ranking for bugs this should be the source of
truth. For now, choose the package with the less amount of dependencies
(choose ``rcpputils`` in priority, then ``rmw*`` then ``rcl*``
packages). You can print the packages dependency tree in your terminal
using the following command:

.. code:: bash

    # We exclude ament packages as they are part of the buildchain / tooling
    # and not part of ROS2.
    $ colcon graph --packages-skip-regex 'ament.*' --packages-up-to rcl
    fastcdr                               +     *                      * *  * *............
    gtest_vendor                           +     *    . .   ...  . ..                    ..
    osrf_pycommon                           +     *   .     ...                           .
    [... snip ...]
    test_msgs                                                                            +*
    rcl                                                                                   +

You will want to choose a package after ``rcpputils`` but as high as
possible in the pyramid.

For the sake of example, we will choose to work on ``rcpputils`` (this
bug has been solved by `this
PR <https://github.com/ros2/rcpputils/pull/9>`__). You can guess which
package has issues by looking at the grep output (if the bug appears in
``rcpputils/*.log``, ``rcpputils`` needs some investigations).

Fixing the bug
--------------

From this point, I suggest having two shells. I personally use i3+tmux
and divide vertically the window in two. The “test shell” is to run the
binaries, the “editor shell” one is to edit the source (I use vim).

*Test shell*: ``cd ~/ros2_asan_ws/build-asan/rcpputils`` *Source shell*:
``cd ~/ros2_asan_ws/src/ros2/rcpputils``

Reproducing the bug
~~~~~~~~~~~~~~~~~~~

In the test shell:

.. code:: bash

    `cd ~/ros2_asan_ws/build-asan/rcpputils
    `# We use CTEST_OUTPUT_ON_FAILURE to force CTest to display more information
    # on failure.
    CTEST_OUTPUT_ON_FAILURE=1 make test
    # The previous line is equivalent to:
    CTEST_OUTPUT_ON_FAILURE=1 ctest .

Running ``ctest`` instead of make allows you to specify the exact flags
``ctest`` will use. For instance, ``ctest -R uncrustify`` will only run
the tests containing the string ``uncrustify`` (useful to fix C++ coding
style issues quickly).

After running the test suite, you can realize that ``test_basic`` is
failing. Let's run the test manually:

.. code:: bash

    `./test_basic
    Running main() from ../../../install-asan/gtest_vendor/src/gtest_vendor/src/gtest_main.cc
    [==========] Running 7 tests from 1 test case.
    [----------] Global test environment set-up.
    [----------] 7 tests from test_tsa
    [ RUN      ] test_tsa.libcxx_types
    [       OK ] test_tsa.libcxx_types (0 ms)
    [ RUN      ] test_tsa.capability
    [       OK ] test_tsa.capability (0 ms)
    [ RUN      ] test_tsa.ptr_guard
    [       OK ] test_tsa.ptr_guard (0 ms)
    [ RUN      ] test_tsa.shared_capability
    [       OK ] test_tsa.shared_capability (0 ms)
    [ RUN      ] test_tsa.return_capability
    [       OK ] test_tsa.return_capability (0 ms)
    [ RUN      ] test_tsa.try_acquire
    [       OK ] test_tsa.try_acquire (0 ms)
    [ RUN      ] test_tsa.acquire_ordering
    [       OK ] test_tsa.acquire_ordering (0 ms)
    [----------] 7 tests from test_tsa (0 ms total)

    [----------] Global test environment tear-down
    [==========] 7 tests from 1 test case ran. (0 ms total)
    [  PASSED  ] 7 tests.

    =================================================================
    ==30859==ERROR: LeakSanitizer: detected memory leaks

    Direct leak of 4 byte(s) in 1 object(s) allocated from:
        #0 0x7fbefcd0b458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
        #1 0x5620b4c650a9 in FakeGuarded::FakeGuarded() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x190a9)
        #2 0x5620b4c63444 in **test_tsa_shared_capability_Test**::TestBody() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x17444)
        #3 0x5620b4cdc4fd in void testing::internal::HandleSehExceptionsInMethodIfSupported<testing::Test, void>(testing::Test*, void (testing::Test::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x904fd)
        #4 0x5620b4cce1e7 in void testing::internal::HandleExceptionsInMethodIfSupported<testing::Test, void>(testing::Test*, void (testing::Test::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x821e7)
        #5 0x5620b4c79f0f in testing::Test::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2df0f)
        #6 0x5620b4c7b33a in testing::TestInfo::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2f33a)
        #7 0x5620b4c7bede in testing::TestCase::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2fede)
        #8 0x5620b4c96fef in testing::internal::UnitTestImpl::RunAllTests() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x4afef)
        #9 0x5620b4cdefb0 in bool testing::internal::HandleSehExceptionsInMethodIfSupported<testing::internal::UnitTestImpl, bool>(testing::internal::UnitTestImpl*, bool (testing::internal::UnitTestImpl::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x92fb0)
        #10 0x5620b4cd04b0 in bool testing::internal::HandleExceptionsInMethodIfSupported<testing::internal::UnitTestImpl, bool>(testing::internal::UnitTestImpl*, bool (testing::internal::UnitTestImpl::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x844b0)
        #11 0x5620b4c93d83 in testing::UnitTest::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x47d83)
        #12 0x5620b4c672d2 in RUN_ALL_TESTS() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x1b2d2)
        #13 0x5620b4c67218 in main (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x1b218)
        #14 0x7fbefc09bb96 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x21b96)

    Direct leak of 4 byte(s) in 1 object(s) allocated from:
        #0 0x7fbefcd0b458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
        #1 0x5620b4c650a9 in FakeGuarded::FakeGuarded() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x190a9)
        #2 0x5620b4c62d4b in **test_tsa_capability_Test**::TestBody() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x16d4b)
        #3 0x5620b4cdc4fd in void testing::internal::HandleSehExceptionsInMethodIfSupported<testing::Test, void>(testing::Test*, void (testing::Test::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x904fd)
        #4 0x5620b4cce1e7 in void testing::internal::HandleExceptionsInMethodIfSupported<testing::Test, void>(testing::Test*, void (testing::Test::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x821e7)
        #5 0x5620b4c79f0f in testing::Test::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2df0f)
        #6 0x5620b4c7b33a in testing::TestInfo::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2f33a)
        #7 0x5620b4c7bede in testing::TestCase::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x2fede)
        #8 0x5620b4c96fef in testing::internal::UnitTestImpl::RunAllTests() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x4afef)
        #9 0x5620b4cdefb0 in bool testing::internal::HandleSehExceptionsInMethodIfSupported<testing::internal::UnitTestImpl, bool>(testing::internal::UnitTestImpl*, bool (testing::internal::UnitTestImpl::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x92fb0)
        #10 0x5620b4cd04b0 in bool testing::internal::HandleExceptionsInMethodIfSupported<testing::internal::UnitTestImpl, bool>(testing::internal::UnitTestImpl*, bool (testing::internal::UnitTestImpl::*)(), char const*) (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x844b0)
        #11 0x5620b4c93d83 in testing::UnitTest::Run() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x47d83)
        #12 0x5620b4c672d2 in RUN_ALL_TESTS() (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x1b2d2)
        #13 0x5620b4c67218 in main (/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcpputils/test_basic+0x1b218)
        #14 0x7fbefc09bb96 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x21b96)

    SUMMARY: AddressSanitizer: 8 byte(s) leaked in 2 allocation(s).   `

The stack trace explains where the problem happens. In this case we have
two tests leaking memory. We can guess this function is actually the
test defined in ``TEST(test_tsa, shared_capability)``.

You can now fix the issue by modifying the code. In the test shell, you
can compile the test again and run the updated binary:

.. code:: bash

    `cd ~/ros2_asan_ws/build-asan/rcpputils
    make && ./test_basic`

*Note*: if you'd rather work from the root directory of the workspace,
you could run ``make -C build-asan/rcpputils``.

If the test suite is emitting too many warning, use ``--gtest_filter=``
to only run the test case you are looking to fix. This will keep the
amount of ASAN errors under control.

Iterate until the bug is fixed.

Cleaning Up the Code
~~~~~~~~~~~~~~~~~~~~

Never send a PR without running ``make test`` locally. If the
``uncrustify`` test fails, it means the coding style is not followed
anymore. This can be fixed easily:

.. code:: bash

    # Extract the "ament_uncrustify" command line from the test:
    cd ~/ros2_asan_ws/build-asan/.../  # In the package BUILD directory
    ctest . -R '^uncrustify$' -V  # Run only the uncrustify test and print test output.UpdateCTestConfiguration  from :/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/CTestConfiguration.ini
    # CTest output, the line you are looking for is in **BOLD**
    Parse Config file:/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/CTestConfiguration.ini
     Add coverage exclude regular expressions.
    SetCTestConfiguration:CMakeCommand:/usr/bin/cmake
    UpdateCTestConfiguration  from :/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/CTestConfiguration.ini
    Parse Config file:/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/CTestConfiguration.ini
    Test project /home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils
    Constructing a list of tests
    Done constructing a list of tests
    Updating test list for fixtures
    Added 0 tests to meet fixture requirements
    Checking test dependency graph...
    Checking test dependency graph end
    test 34
        Start 34: uncrustify

    34: Test command: /usr/bin/python3 "-u" "/home/ANT.AMAZON.COM/tmoulard/ros2_ws/install-asan/ament_cmake_test/share/ament_cmake_test/cmake/run_test.py" "/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/test_results/rcutils/uncrustify.xunit.xml" "--package-name" "rcutils" "--output-file" "/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/ament_uncrustify/uncrustify.
    txt" "--command" "/home/ANT.AMAZON.COM/tmoulard/ros2_ws/install-asan/ament_uncrustify/bin/ament_uncrustify" "--xunit-file" "/home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/test_results/rcutils/uncrustify.xunit.xml"
    34: Test timeout computed to be: 60
    34: -- run_test.py: invoking following command in '/home/ANT.AMAZON.COM/tmoulard/ros2_ws/src/ros2/rcutils':
    34:  - **/home/ANT.AMAZON.COM/tmoulard/ros2_ws/install-asan/ament_uncrustify/bin/ament_uncrustify --xunit-file /home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/test_results/rcutils/uncrustify.xunit.xml**
    # [...snip... more CTest output]
    # Copy the line in **BOLD** before (from YOUR term as paths will differ).
    # Go to your package SOURCE directory:
    cd ~/ros2_asan_ws/src/.../
    # Paste the line in your term, add --reformat as an extra flag and run the command.
    /home/ANT.AMAZON.COM/tmoulard/ros2_ws/install-asan/ament_uncrustify/bin/ament_uncrustify --xunit-file /home/ANT.AMAZON.COM/tmoulard/ros2_ws/build-asan/rcutils/test_results/rcutils/uncrustify.xunit.xml \
    **    --reformat**
    # Your code is now correctly formatted!

Sending the PR for review
~~~~~~~~~~~~~~~~~~~~~~~~~

Once the bug is fixed and the PR is ready to be opened:

.. code:: bash

    git add -p
    git commit -s  # Always include a DCO in your commits.
    git push origin master:thomas-moulard/fix-my-bug

Open a PR and you're done!

Appendix - ASAN/TSAN Issues Zoology
===================================

ASAN
----

Memory Leak
~~~~~~~~~~~

-  Test log output: ``ERROR: LeakSanitizer: detected memory leaks``
-  XML tag: detected-memory-leaks

At the end of the execution, ASAN reports as a single error the list of
all memory chunks which never were freed. This happens as a final single
error message because until the process exits, there is a possibility
this memory can be freed.

Example:

.. code:: bash

    1: ==32481==ERROR: LeakSanitizer: detected memory leaks
    1:
    1: Direct leak of 4 byte(s) in 1 object(s) allocated from:
    1:     #0 0x7f7d99dac458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
    [snip]
    1:
    1: Direct leak of 4 byte(s) in 1 object(s) allocated from:
    1:     #0 0x7f7d99dac458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
    [snip]
    1:
    1: SUMMARY: AddressSanitizer: 8 byte(s) leaked in 2 allocation(s).

Heap Overflow
~~~~~~~~~~~~~

-  Test log output:
   ``==12958==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x60c0000006b8 at pc 0x* bp 0x* sp 0x*``
-  XML tag: heap-buffer-overflow

This happens when the program accesses an unallocated chunk of memory.

Example:

.. code:: bash

    56: =================================================================
    56: ==12958==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x60c0000006b8 at pc 0x7f1d2a9d7733 bp 0x7ffc9668be70 sp 0x7ffc9668b618
    56: READ of size 511 at 0x60c0000006b8 thread T0
    56:     #0 0x7f1d2a9d7732  (/usr/lib/x86_64-linux-gnu/libasan.so.4+0x79732)
    [snip]
    56:
    56: 0x60c0000006b8 is located 0 bytes to the right of 120-byte region [0x60c000000640,0x60c0000006b8)
    56: allocated by thread T0 here:
    56:     #0 0x7f1d2aa3e458 in operator new(unsigned long) (/usr/lib/x86_64-linux-gnu/libasan.so.4+0xe0458)
    [snip]
    56:
    56: SUMMARY: AddressSanitizer: heap-buffer-overflow (/usr/lib/x86_64-linux-gnu/libasan.so.4+0x79732)
    56: Shadow bytes around the buggy address:
    56:   0x0c187fff8080: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
    56:   0x0c187fff8090: fa fa fa fa fa fa fa fa fd fd fd fd fd fd fd fd
    56:   0x0c187fff80a0: fd fd fd fd fd fd fd fd fa fa fa fa fa fa fa fa
    56:   0x0c187fff80b0: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
    56:   0x0c187fff80c0: fa fa fa fa fa fa fa fa 00 00 00 00 00 00 00 00
    56: =>0x0c187fff80d0: 00 00 00 00 00 00 00**[fa]**fa fa fa fa fa fa fa fa
    56:   0x0c187fff80e0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    56:   0x0c187fff80f0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    56:   0x0c187fff8100: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    56:   0x0c187fff8110: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    56:   0x0c187fff8120: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    56: Shadow byte legend (one shadow byte represents 8 application bytes):
    56:   Addressable:           00
    56:   Partially addressable: 01 02 03 04 05 06 07
    56:   Heap left redzone:       fa
    56:   Freed heap region:       fd
    56:   Stack left redzone:      f1
    56:   Stack mid redzone:       f2
    56:   Stack right redzone:     f3
    56:   Stack after return:      f5
    56:   Stack use after scope:   f8
    56:   Global redzone:          f9
    56:   Global init order:       f6
    56:   Poisoned by user:        f7
    56:   Container overflow:      fc
    56:   Array cookie:            ac
    56:   Intra object redzone:    bb
    56:   ASan internal:           fe
    56:   Left alloca redzone:     ca
    56:   Right alloca redzone:    cb
    56: ==12958==ABORTING

In this case, we can see that this is an off-by-on issue where the
memory in **BOLD** is illegally accessed. The position of this cell
(first cell after the end of the allocated memory) is leading us to
think that this is an off-by-one bug.

TSAN
----

Data Race
~~~~~~~~~

-  Test log output: ``WARNING: ThreadSanitizer: data race (pid=*)``
-  XML tag: ``data-races``

Two threads writes to (or read and write) the same chunk of memory
without holding a lock. The result of this operation is
non-deterministic and can lead to crashes, dead-lock, etc.

Refactoring the code using Thread Safety Annotations is the easiest way
forward. Those extensions will prevent bad patterns.

Example of error:

.. code:: bash

    30: ==================
    30: WARNING: ThreadSanitizer: data race (pid=23489)
    30:   Write of size 8 at 0x7ba000000060 by main thread (mutexes: write M3845, write M3798):
    30:     #0 close <null> (libtsan.so.0+0x2f447)
    [snip]
    30:
    30:   Previous read of size 8 at 0x7ba000000060 by thread T2:
    30:     #0 recvmsg <null> (libtsan.so.0+0x3b48b)
    [snip]
    30:   Location is file descriptor 6 created by main thread at:
    30:     #0 socket <null> (libtsan.so.0+0x2ee83)
    [snip]
    30:   Mutex M3845 (0x7fea26ffe800) created at:
    30:     #0 pthread_mutex_lock <null> (libtsan.so.0+0x3faeb)
    [snip]
    30:   Mutex M3798 (0x7fea26ffe320) created at:
    30:     #0 pthread_mutex_lock <null> (libtsan.so.0+0x3faeb)
    [snip]
    30:   Thread T2 (tid=23492, finished) created by main thread at:
    30:     #0 pthread_create <null> (libtsan.so.0+0x2bcfe)
    [snip]
    30:
    30: SUMMARY: ThreadSanitizer: data race (/usr/lib/x86_64-linux-gnu/libtsan.so.0+0x2f447) in __interceptor_close
    30: ==================

This error messages describes that the main thread wrote 8 bytes while
T2 reads it. TSAN explains that 0x7ba000000060 is actually mapped to the
file descriptor number 6 and includes where the file descriptor was
open. When the data race happened, mutexes M3845 and M3798 were locked.
TSAN also mentions where those mutexes have been created.

`TSAN doc details what are some typical data
races <https://github.com/google/sanitizers/wiki/ThreadSanitizerPopularDataRaces#race-during-destruction>`__.
This race condition is documented under the sections “Race on a file
descriptor” and “Race during exit”.

Lock Order Inversion
~~~~~~~~~~~~~~~~~~~~

-  Test log output:
   ``WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=*)``
-  XML tag: ``lock-order-inversion``

Lock order inversions happen when a code path allows the same mutex to
be locked twice before the original lock can be released. If the code
path happens, the process will enter dead-lock.

Refactoring the code using Thread Safety Annotations is the easiest way
forward. Those extensions will prevent bad patterns.

Example of error:

.. code:: bash

    34: ==================
    34: WARNING: ThreadSanitizer: lock-order-inversion (potential deadlock) (pid=23572)
    34:   Cycle in lock order graph: M8016590817765616 (0x000000000000) => M56430286811999312 (0x000000000000) => M8016590817765616
    34:
    34:   Mutex M56430286811999312 acquired here while holding mutex M8016590817765616 in thread T12:
    34:     #0 pthread_mutex_lock <null> (libtsan.so.0+0x3faeb)
    [snip]
    34:
    34:   Mutex M8016590817765616 acquired here while holding mutex M56430286811999312 in thread T12:
    34:     #0 pthread_mutex_lock <null> (libtsan.so.0+0x3faeb)
    [snip]
    34:
    34:   Thread T12 (tid=23609, running) created by main thread at:
    34:     #0 pthread_create <null> (libtsan.so.0+0x2bcfe)
    [snip]
    34:
    34: SUMMARY: ThreadSanitizer: lock-order-inversion (potential deadlock) (/usr/lib/x86_64-linux-gnu/libtsan.so.0+0x3faeb) in __interceptor_pthread_mutex_lock
    34: ==================

TSAN detected a code path where the mutex M8016590817765616 is locked
twice without releasing the lock in between. The error message details
the stack trace when each mutex is being locked. In order:

-  Mutex M8016590817765616 gets locked a first time (this is OK - we
   don't know where this happens)
-  Mutex M56430286811999312 gets locked (this is OK - the first stack
   trace explains where this happens)
-  Mutex M8016590817765616 gets locked a *second* time (this is bad -
   the second stack trace explains where this happens)

Additionally, the error message explains that all locks happen in threat
T12 (the last stack trace details which thread is T12).

Heap Use After Free
~~~~~~~~~~~~~~~~~~~

-  Test log output:
   ``==5587==ERROR: AddressSanitizer: heap-use-after-free on address 0x61400000fe44 at pc 0x47b55f bp 0x7ffc36b28200 sp 0x7ffc36b281f8``
-  XML tag: ``heap-use-after-free``

An already freed memory block is accessed.

The code must be rewritten to avoid this problem. For instance, memory
ownership can be improved to avoid misuse. unique\_ptr should be used
whenever a memory chunk has a single owner (over raw C pointers). Thread
safety annotations are not useful in this case.

Unsafe Call inside signal Callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  Test log output:
   ``WARNING: ThreadSanitizer: signal-unsafe call inside of a signal (pid=*)``
-  XML tag: ``signal-unsafe-call-inside-signal``

See `man 7
signal-safety <http://man7.org/linux/man-pages/man7/signal-safety.7.html>`__.
Only some functions are allowed in signal handlers, unsafe functions
must never be used.

Signal handlers should contain as little code as possible. If some work
happening in the callback can be moved back into an application thread,
this should help solving this problem.

Example of error:

.. code:: bash

    32: ==================
    32: WARNING: ThreadSanitizer: signal-unsafe call inside of a signal (pid=5630)
    32:     #0 malloc <null> (libtsan.so.0+0x2ae13)
    32:     #1 _IO_file_doallocate <null> (libc.so.6+0x7e18b)
    32:     #2 rcl_logging_multiple_output_handler ../../src/ros2/rcl/rcl/src/rcl/logging.c:132 (librcl.so+0x1560f)
    32:     #3 rcutils_log ../../src/ros2/rcutils/src/logging.c:407 (librcutils.so+0xabf0)
    32:     #4 rclcpp::SignalHandler::signal_handler(int, siginfo_t*, void*) ../../src/ros2/rclcpp/rclcpp/src/rclcpp/signal_handler.cpp:221 (librclcpp.so+0x157c93)
    [snip]
    32:
    32: SUMMARY: ThreadSanitizer: signal-unsafe call inside of a signal (/usr/lib/x86_64-linux-gnu/libtsan.so.0+0x2ae13) in malloc
    32: ==================

In this example, the signal handler is logging a string. This logging
code is allocating memory using ``malloc()`` which is not an allowed
function in signal handlers.

Signal handler spoils errno
~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  Test log output: ``WARNING: ThreadSanitizer: signal handler spoils errno``
-  XML tag: ``signal-handler-spoils-errno``

``errno`` value must never be modified in signal handlers. See “unsafe
call inside signal callback”. The best solution is to avoid placing
complex code in signal callbacks. Example of bug this problem can
introduce (in pseudo-code):

.. code:: c

    void signal_handler() {
      my_function_modifying_errno();  // Will fail and set errno to ABCD
      if (errno == ABCD) { /* do something */ }
    }

    int main() {
      install_signal_handler(&signal_handler);
      my_other_function_modifying_errno();  // Will fail and set errno to EFGH.
      // A signal is received! signal_handler() gets executed here.
      if (errno == ABCD) { /* do something */ }  // <- this gets executed
      else if (errno == EFGH) {
          /* do something else */ }  // <- this should have been executed
    }

As you can see, modifying errno value in signal handlers is creating
issues because after the signal finishes executing, any ``errno``
checking code will think its checking the ``errno`` value of the
function the thread just executed whereas it is actually checking the
errno value set by the signal handler call.unsafe-call-ins
