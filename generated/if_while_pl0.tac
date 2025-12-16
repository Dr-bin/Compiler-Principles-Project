x = 3
y = 5
if not x < y goto L1
max = y
goto L2
L1:
max = x
L2:
print(max)
i = 0
L3:
if not i < 5 goto L4
print(i)
t1 = i + 1
i = t1
goto L3
L4:
