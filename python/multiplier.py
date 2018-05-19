#!/usr/bin/env python

sign_bit = 1<<31
mask64 = 0xffffffffffffffff
mask32 = 0xffffffff
mask31 = 0x7fffffff
class multdiv:
    def __init__(self):
        self.accumulator = 0 # 64 bits
        self.multiplier = 0 # 32 bits
        self.multiplicand = 0 # 32 bits
        self.stage = 0 # 4 bits (maybe 5)
    def combinatorial(self, mult4, areg, subtract_acc, acc, shift):
        sel0123 = mult4 & 3
        sel048c = (mult4>>2) & 3
        stage1_0 = 0
        stage1_1 = areg
        stage1_2 = areg<<1
        stage1_3 = stage1_2 + stage1_1 # 34-bit ADDER
        stage1_4 = stage1_1 << 2
        stage1_8 = stage1_2 << 2
        stage1_c = stage1_3 << 2
        if sel0123==0: mux_0123 = stage1_0
        if sel0123==1: mux_0123 = stage1_1
        if sel0123==2: mux_0123 = stage1_2
        if sel0123==3: mux_0123 = stage1_3
        if sel048c==0: mux_048c = stage1_0
        if sel048c==1: mux_048c = stage1_4
        if sel048c==2: mux_048c = stage1_8
        if sel048c==3: mux_048c = stage1_c
        stage2 = mux_0123 + mux_048c # 36-bit adder
        if subtract_acc:
            acc_result = ((stage2<<shift) - acc) & mask64
            pass
        else:
            acc_result = ((stage2<<shift) + acc) & mask64
            pass
        return acc_result
    def div_init(self, a, b, signed=False):
        self.divisor      = b & mask32
        self.stage = 0
        self.accumulator = (a&mask32)<<32
        while (self.divisor & sign_bit)==0:
            self.divisor  = self.divisor<<1
            self.stage = self.stage + 1
            pass
        while (self.accumulator & (sign_bit<<32))==0:
            self.accumulator  = self.accumulator<<1
            self.stage = self.stage - 1
            pass
        print "%08x %08x  %016x %08x %d"%(a&mask32,b&mask32,self.accumulator,self.divisor,self.stage)
        pass
    def mul_init(self, a, b, sa=False, sb=False):
        self.multiplier   = a & mask32
        self.multiplicand = b & mask32
        self.stage = 0
        acc_in = 0
        add_in = 0
        if (sa and (a&sign_bit)):
            acc_in = (b&mask32)<<32
            if sb: acc_in = acc_in & (mask31<<32)
        if (sb and (b&sign_bit)):
            add_in = a&mask32
            if sa: add_in = add_in & mask31
        next_acc = self.combinatorial(mult4=1, areg=add_in, subtract_acc=0, acc=acc_in, shift=32)
        self.accumulator = next_acc & mask64
        pass
    def div_init(self, a, b, signed=False):
        self.divisor      = b & mask32
        self.stage = 0
        self.accumulator = (a&mask32)<<32
        while (self.divisor & sign_bit)==0:
            self.divisor  = self.divisor<<1
            self.stage = self.stage + 1
            pass
        while (self.accumulator & (sign_bit<<32))==0:
            self.accumulator  = self.accumulator<<1
            self.stage = self.stage - 1
            pass
        print "%08x %08x  %016x %08x %d"%(a&mask32,b&mask32,self.accumulator,self.divisor,self.stage)
        pass
    def mul_step(self):
        next_acc = self.combinatorial(mult4 = self.multiplier & 15,
                                      areg = self.multiplicand,
                                      subtract_acc = (self.stage==0),
                                      acc = self.accumulator,
                                      shift = self.stage*4)
        self.accumulator = next_acc
        self.stage = self.stage + 1
        self.multiplier = self.multiplier >> 4
        return (self.multiplier==0)
    def div_step(self): # uses 64-bit accumulator adder
        next_acc = self.combinatorial( mult4 = 1,
                                       shift = 32,
                                       subtract_acc = True,
                                       acc = self.accumulator,
                                       areg = self.divisor )
        if ((next_acc>=0) and (self.stage>=0)):
            next_acc = -next_acc + (1<<self.stage)
            self.accumulator = next_acc
            pass
        self.divisor  = self.divisor >> 1
        self.stage = self.stage-1
        return self.stage<0
    def div_remainder(self, a, b, signed=False):
        return (self.accumulator>>32) & mask32
    def div_result(self, a, b, signed=False):
        return self.accumulator & mask32

def test_mult(test_a,test_b):
    test_a = test_a & mask32
    test_b = test_b & mask32
    for (sa,sb) in [(False,False),(True,True), (False,True), (True,False)]:
        for (na,nb) in [(1,1), (-1,1), (1,-1), (-1,-1)]:
            a = (na * test_a) & mask32
            b = (nb * test_b) & mask32
            if (a & sign_bit): a = a - (1<<32)
            if (b & sign_bit): b = b - (1<<32)
            x = multdiv()
            x.mul_init(a,b,sa,sb)
            while not x.mul_step():
                pass
            r = x.accumulator
            m = (a&mask32) * (b&mask32) # unsigned
            if sa and sb:m = (a * b)&mask64 # signed
            if sa and (not sb):m = (a * (b & mask32))&mask64
            if sb and (not sa):m = (b * (a & mask32))&mask64
            err = ""
            if (r!=m) : err = "DIFFERENT"
            print("%08x*%08x : %13d * %13d : %26d : %016x  (%016x) %s" % ((a&mask32),(b&mask32),a,b,r,r,m,err))

def test_div(test_a,test_b):
    test_a = test_a & mask32
    test_b = test_b & mask32
    for signed in [False,True]:
        for (na,nb) in [(1,1), (-1,1), (1,-1), (-1,-1)]:
            a = (na * test_a) & mask32
            b = (nb * test_b) & mask32
            if (a & sign_bit): a = a - (1<<32)
            if (b & sign_bit): b = b - (1<<32)
            x = multdiv()
            x.div_init(a,b,signed)
            while not x.div_step():
                pass
            r = x.div_result(a,b,signed)
            rem = x.div_remainder(a,b,signed)
            m    = (a&mask32) / (b&mask32) # unsigned
            mrem = (a&mask32) % (b&mask32) # unsigned
            err = ""
            if (r!=m) : err = "DIFFERENT"
            print("%08x/%08x : %13d / %13d : %13d %13d: %08x %08x  (%08x %08x) %s" % ((a&mask32),(b&mask32),a,b,r,rem,r,rem,m,mrem,err))

if True:
    test_mult(4,5)
    test_mult(0x40000000,5)
    test_mult(5,0x40000000)
    test_mult(0x89abcdef,5)
    test_mult(5,0x89abcdef)
    test_mult(0x12345670,0xdeadbeef)
    test_mult(0xdeadbeef,0x12345670)

if True:
    test_div(4,5)
    test_div(0x40000000,5)
    test_div(5,0x40000000)
    test_div(0x89abcdef,5)
    test_div(5,0x89abcdef)
    test_div(0x12345670,0xdeadbeef)
    test_div(0xdeadbeef,0x12345670)