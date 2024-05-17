! D1Ar1, D0Ar2 and D1Ar3 are args for minim_disable, don't clobber them
! A0.2: source
! A0.3: destination
! A0.4: key

! set DUARITHMODE = META_DUARITH_SPLIT16 0x1
! set AU0ADDRMODE = META_AUADDR_MODULO 0x300
! set AU1ADDRMODE = META_AUADDR_BITREV8 0x4000
MOV D0.4, TXMODE
OR D0.4, D0.4, #0x4301
MOV TXMODE, D0.4

! modulo for addressing
MOV D0.4, #0x1000
MOV TXMRSIZE, D0.4
! copy source to other address unit
MOV A1.2, A0.2
! setup increment for bitreversed addressing
MOV A1.3, #0x0800

! setup cmul loop counter
MOV TXRPT, #511
cmul_loop:
    ! load value and key
    GETL D1.4, D0.4, [A0.2++]
    GETL D1.6, D0.6, [A0.4++]

    ! interpret each 16 bit half as two 8 bit numbers
    ! shift each number to the top 8 bits
    LSLDP D0.5, D0.4, #8
    ANDDP D0.4, D0.4, #0xff00
    LSLDP D0.7, D0.6, #8
    ANDDP D0.6, D0.6, #0xff00

    ! perform complex multiplication of both halves
    DSPMULDC D0.5, D0.5, D0.7
    DSPMULDC D0.4, D0.4, D0.6

    ! merge the result back
    LSLDP D0.4, D0.4, #8
    ANDDP D0.5, D0.5, #0xff
    ORDP D0.4, D0.4, D0.5

    ! store the result
    SETL [A0.3++], D0.4, D1.4
BR cmul_loop

! loop to shuffle bytes with bitreversed addressing
MOV TXRPT, #0xfff
cswap_loop:
    GETB D0.4, [A0.3++]
    SETB [A1.2+A1.3++], D0.4
BR cswap_loop

! set DUARITHMODE = META_DUARITH_32X32L 0x3
MOV D0.4, TXMODE
OR D0.4, D0.4, #0x3
MOV TXMODE, D0.4

! setup outer loop counter
MOV D0.0, #20
main_loop:
    ! setup cmul loop counter
    MOV TXRPT, #511
    mul_loop:
        ! load value and key
        GETL D1.4, D0.4, [A0.2++]
        GETL D1.6, D0.6, [A0.4++]

        ! perform multiplication
        DSPMULD D0.4, D0.4, D0.6

        ! store the result
        SETL [A0.3++], D0.4, D1.4
    BR mul_loop

    ! loop to shuffle bytes with bitreversed addressing
    ADD A1.2, A1.2, #0x800 ! inc by one to make swapping effective
    MOV TXRPT, #0xfff
    swap_loop:
        GETB D0.4, [A0.3++]
        SETB [A1.2+A1.3++], D0.4
    BR swap_loop

    SUBS D0.0, D0.0, #1
BNZ main_loop

! disable duarith
! set ADDRMODE to linear
MOV D0.4, TXMODE
ANDMB D0.4, D0.4, #0x88fc
MOV TXMODE, D0.4

.align4
