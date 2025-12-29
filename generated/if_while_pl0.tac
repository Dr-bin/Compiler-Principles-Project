x = 3
y = 5
max = x
t1 = x < y
max = y
t2 = not t1
if t2 goto L1
L1:
param max
call write, 1
i = 0
t3 = i < 5
param i
call write, 1
t4 = i + 1
i = t4
L2:
t5 = not t3
if t5 goto L3
goto L2
L3: