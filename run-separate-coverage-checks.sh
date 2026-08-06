foreach file in `ls test/*.py`
echo "\n#######################\n" >>coverage_results.txt
echo $file >> coverage_results.txt
coverage erase
coverage run -m pytest $file >> coverage_results.txt
coverage report >> coverage_results.txt
end


echo "\n#######################\n" >>coverage_results.txt
echo "All" >>coverage_results.txt
coverage erase
coverage run -m pytest test >>coverage_results.txt
coverage report >>coverage_results.txt
