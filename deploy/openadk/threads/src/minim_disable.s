! D1Ar1 should contain the pointer to the MMIO map to restore everything
! D0Ar2 cointains the trampoline address
! D1Ar3 contains saved TXMASKI
! We want that in A0.2
MOV A0.2, D1Ar1

    ! This trampoline invocation is taken from the main source code, keep it in sync!
    ! This is shorter, since
    !  - we use TXENABLE_STOPPED rather than TXENABLE_OFF, so the MMU setup should still be sane, and
    !  - we already know the other thread is stopped

    ! PC = &trampoline
    ! map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) &trampoline;
    MOV A0.3, A0.2
    ADD A0.3, A0.3, #0xfff0 ! GLOBAL_REG(META_TXUXXRXDT)
    ! Reload trampoline addr from wherever it was saved
    ! TODO: Adjust from D0Ar2 to wherever it was saved.
    SETD [A0.3], D0Ar2

    ! map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_PC | (META_PC << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;
    MOV D1Ar1, #0x1005
    SETD [A0.3+#8], D1Ar1

    ! write saved_txmaski to new_txmaski
    ! D1Ar5 = saved_txmaski
    ! map[GLOBAL_REG(META_TXUXXRXDT)] = saved_txmaski;
    SETD [A0.3], D1Ar3

    ! map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR1 << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;
    MOV D1Ar1, #0x1012
    SETD [A0.3+#8], D1Ar1

    ! map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_PC | (META_PC << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;

    ! D1Ar1 = map
    ! map[GLOBAL_REG(META_TXUXXRXDT)] = (uint32_t) map;
    MOV D1Ar1, A0.2
    SETD [A0.3], D1Ar1

    ! map[GLOBAL_REG(META_TXUXXRXRQ)] = META_UNIT_D1 | (META_D1AR1 << 4) | (THREAD_TEMP << 12) | TXUXXRXRQ_WRITE;
    MOV D1Ar1, #0x1032
    SETD [A0.3+#8], D1Ar1

    ! Start the target thread by setting TXENABLE
    ! map[THREAD_REG(THREAD_TEMP, META_TXENABLE)] = TXENABLE_RUNNING;
    MOV A0.3, A0.2
    ADD A0.3, A0.3, #0x1000
    MOV D1Ar1, #1
    SETD [A0.3], D1Ar1

    ! Suspend ourselves. We'll restart in META mode...
    ! map[THREAD_REG(THREAD_ORIG, META_TXENABLE)] = TXENABLE_STOPPED;
    MOV D1Ar1, #6
    SETD [A0.2], D1Ar1

    ! This will update the PC before suspension
    B end
    ! make sure this is aligned or META mode will not be happy
    .align4
end:
