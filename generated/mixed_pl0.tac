n = 5
sum = 0
i = 1
L1:
if not i <= n goto L2
t1 = sum + i
sum = t1
t2 = i + 1
i = t2
goto L1
L2:
if not sum > 10 goto L3
print(sum)
goto L4
L3:
print(n)
L4:
