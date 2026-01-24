# Simple Calculator
print("+ for addition \n - for subtraction \n"
" * for multiplication \n /  for division \n Percent sign for modulus \n"
"Any other symbol\character for average")
num, oper, num2 = input().split()
num = float(num)
oper = str(oper)
num2 = float(num2)
print(num, oper, num2)
if oper == "+":
     
        print(num + num2)
      
elif oper == "-":
     
        print(num - num2)
      
elif oper == "*":
     
        print(num * num2)
      
elif oper == "/":
    if num != 0 and num2 != 0:
         
            print(num / num2)
              
    else:
         
            print("0 can't be used for division")
          
elif oper == "%":
    if num != 0 & num2 != 0:
          
            print(num % num2)
                   
    else:
         
            print("0 can't be used to find modulus")
          
else:
     
        print((num+num2)/2)
      