x = 3
y = 5
max = x
t1 = x < y
t2 = not t1
if t2 goto L1
max = y
L1:
param max
call write, 1
i = 0
L2:
t3 = i < 5
t4 = not t3
if t4 goto L3
param i
call write, 1
t5 = i + 1
i = t5
goto L2
L3:
