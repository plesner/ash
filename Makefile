SCRIPT=a
ALL_PYS=$(shell find -name \*.py)

$(SCRIPT):	$(ALL_PYS)
			rm -f $(SCRIPT)
			cat src/a.py | grep -v "IMPORT\|STRIP" > $(SCRIPT)
			cat `cat src/a.py | grep "IMPORT" | sed "s|.*IMPORT(\([^)]*\))|src/ash/\1|g"` >> $(SCRIPT)
			chmod a+x $(SCRIPT)

tests:		$(ALL_PYS)
			python test/*.py
