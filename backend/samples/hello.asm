; Sample 8086 assembly program
; Tests MOV, ADD, LOOP, CALL, RET, conditional jumps

.model small
.stack 100h
.code

main:
    ; Initialize: BX will count 1,2,3,4,5 and accumulate sum in AX
    MOV CX, 5       ; Loop counter
    MOV AX, 0       ; Sum accumulator  
    MOV BX, 0       ; Counter for adding
    
    ; Sum loop: AX = 1+2+3+4+5 = 15
sum_loop:
    INC BX          ; BX = 1, 2, 3, 4, 5
    ADD AX, BX      ; AX += BX
    LOOP sum_loop
    
    ; Double the result via subroutine: AX = 30
    CALL double_ax
    
    ; Test conditional jump: is AX == 30?
    CMP AX, 30
    JE success
    MOV DX, 0       ; Failed
    JMP done
    
success:
    MOV DX, 1       ; Success!
    
done:
    HLT

; Subroutine: doubles AX
double_ax:
    ADD AX, AX
    RET

end main
