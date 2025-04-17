money = 9

mas = [1,2,5,10,50,100,500,1000,2000,5000]
result = [[],[],[],[]]



def rub(money,mas):
    cup = [5,2,2,1]
    for i in range(len(mas) - 1, -1, -1):
        if money >= mas[i]:
            money -= mas[i]
            result.append(mas[i])
    




rub(money,mas)
print(result)
