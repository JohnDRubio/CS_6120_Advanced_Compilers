from RVIRInsns.RVIRInsn import RVIRInsn

class RVIRRegRegInsn(RVIRInsn):
    valid_ops = ['ADD','SUB','MUL','DIV','AND','OR','XOR','SLT','SLTU','SRA','SRL','SLL']
    def __init__(self, op, dst, src1, src2):
        if op.upper() not in self.valid_ops:
            raise ValueError(f"Invalid operation '{op}'. Supported operations are: {', '.join(self.valid_ops)}")
        self.op = op
        self.dst  = dst
        self.src1 = src1
        self.src2 = src2
    
    def emit_asm(self):
        return f'{self.op} {self.dst}, {self.src1}, {self.src2}'

# r = RVIRRegRegInsn('add','x1','x2','x3')
# r = RVIRRegRegInsn('john','x1','x2','x3')   # raises error
# print(r.emit_asm())