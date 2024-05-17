# D1Ar1 is &map
# D1Ar5 is new TXMASKI
.local _trampoline
_trampoline:
    # while (map[THREAD_REG(THREAD_ORIG, META_TXENABLE)] & TXENABLE_RUNNING);
  .L_busy_wait:
    GETD D0FrT, [D1Ar1]
    ANDS D0Ar2, D0FrT, #0x1
    BNE .L_busy_wait

    # D1Ar3 is &map[GLOBAL_REG(META_TXUXXRXDT)]
    MOV D1Ar3, D1Ar1
    ADD D1Ar3, D1Ar3, #0xfff0

    ## Store the map in D1Ar1 in the original thread also
    # map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) map;
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR1 << 4) | (THREAD_ORIG << 12) | TXUXXRXRQ_WRITE;
    MOV D0Ar2, #0x32
    SETD [D1Ar3], D1Ar1
    SETD [D1Ar3+#8], D0Ar2

    ## Store the trampoline in D0Ar2 in the original thread, so it can
    ## call back into it to disable MiniM
    # map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) &trampoline;
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D0 | (META_D0AR2 << 4) | (THREAD_ORIG << 12) | TXUXXRXRQ_WRITE;
    MOV D0Ar2, PC
  .L_local_pc:
    SUB D0Ar2, D0Ar2, #(.L_local_pc - _trampoline)
    MOV D0Ar4, #0x31
    SETD [D1Ar3], D0Ar2
    SETD [D1Ar3+#8], D0Ar4

    ## Switch the original thread to MiniM mode
    # map[THREAD_REG(THREAD_ORIG, META_TXPRIVEXT)] ^= TXPRIVEXT_MINIM;
    MOV D0Ar6, D1Ar1
    GETD D0Ar2, [D0Ar6+#0xe8]
    XOR D0Ar2, D0Ar2, #0x80
    SETD [D0Ar6+#0xe8], D0Ar2

    ## Adjust PC for MiniM mode (see meta_pc_to_virt in QEMU)
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_PC | (META_PC << 4) | (THREAD_ORIG << 12)
    #                                   | TXUXXRXRQ_READ;
    # pc = map[GLOBAL_REG(META_TXUXXRXDT)]
    # map[GLOBAL_REG(META_TXUXXRXDT)] = adjust(pc);
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_PC | (META_PC << 4) | (THREAD_ORIG << 12)
    #                                   | TXUXXRXRQ_WRITE;
    ANDS D0Ar2, D0Ar2, #0x80
    # Z-bit now indicates whether we are switching to META (non-MiniM) mode
    MOVT D0Ar4, #0x1
    ADD D0Ar4, D0Ar4, #5
    SETD [D1Ar3+#8], D0Ar4
    GETD D0Ar2, [D1Ar3]
    # Make sure we don't skip anything. I'm not sure this is 100% right,
    # but it seems to work
    ADDNZ D0Ar2, D0Ar2, #4
    # D0Ar2 now has the current PC value
    # In MiniM mode, we need to double the low bits of the PC, because it will internally be
    # halved again. Vice versa for normal mode.
    LSL D0Ar4, D0Ar2, #8
    LSR D0Ar4, D0Ar4, #7
    LSRZ D0Ar4, D0Ar4, #2
    LSR D0Ar2, D0Ar2, #24
    LSL D0Ar2, D0Ar2, #24
    OR D0Ar2, D0Ar2, D0Ar4
    SETD [D1Ar3], D0Ar2
    MOV D0Ar2, #5
    SETD [D1Ar3+#8], D0Ar2

    ## Toggle ISTAT so we don't take interrupts while in MiniM mode
    # map[THREAD_REG(THREAD_ORIG, META_TXSTATUS)] ^= TXSTATUS_ISTAT;
    #GETD D0Ar2, [D0Ar6+#0x10]
    #XORT D0Ar2, D0Ar2, #0x1
    #SETD [D0Ar6+#0x10], D0Ar2

    ## ISTAT disables some features use TXMASKI to disabled interrupts instead
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_TR | (META_TXMASKI << 4) | (THREAD_ORIG << 12)
    #                                   | TXUXXRXRQ_READ;
    # saved_txmaski = map[GLOBAL_REG(META_TXUXXRXDT)]
    MOVT D0Ar4, #0x1
    ADD D0Ar4, D0Ar4, #0x37
    SETD [D1Ar3+#8], D0Ar4
    GETD D1RtP, [D1Ar3]

    # map[GLOBAL_REG(META_TXUXXRXDT)] = new_txmaski;
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_TR | (META_TXMASKI << 4) | (THREAD_ORIG << 12)
    #                                   | TXUXXRXRQ_WRITE;
    MOV D0Ar4, #0x37
    SETD [D1Ar3], D1Ar5
    SETD [D1Ar3+#8], D0Ar4

    ## Store the original TXMASKI in D1Ar3 in the original thread also
    # map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) map;
    # map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR1 << 4) | (THREAD_ORIG << 12) | TXUXXRXRQ_WRITE;
    MOV D0Ar2, #0x22
    SETD [D1Ar3], D1RtP
    SETD [D1Ar3+#8], D0Ar2

    ## Restart the original thread.
    # map[THREAD_REG(THREAD_ORIG, META_TXENABLE)] = TXENABLE_RUNNING;
    MOV D0Ar2, #0x1
    SETD [D0Ar6], D0Ar2

    ## Bye.
    # map[THREAD_REG(THREAD_TEMP, META_TXENABLE)] = TXENABLE_STOPPED;
    ADD D0Ar2, D0Ar2, #0x5
    SETD [D0Ar6+#0x1000], D0Ar2

    # XXX: workaround
    B .
    ## syscall(SYS_exit_group, 0)
    MOV D1Re0, #94
    XOR D1Ar1, D1Ar1, D1Ar1
    SWITCH #0x440001
