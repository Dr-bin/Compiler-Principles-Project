n = 5
sum = 0
i = 1
L1:
t1 = i <= n
t2 = not t1
if t2 goto L2
t3 = sum + i
sum = t3
t4 = i + 1
i = t4
goto L1
L2:
t5 = sum > 10
t6 = not t5
if t6 goto L3
param sum
call write, 1
L3:
param n
call write, 1
