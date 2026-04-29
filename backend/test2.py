import traceback
import io

f = open('err3.log', 'w', encoding='utf-8')
try:
    import main
    print("OK")
except Exception as e:
    traceback.print_exc(file=f)
f.close()
