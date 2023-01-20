const input2 = document.getElementById("dropdownInput2")
const block2 = document.getElementById("dropdownBlock2")




const replaceElements = (el, inp) => inp.addEventListener("input", (event) => {
    [...el.children].forEach((element) => element.tagName === "DIV" && (element.getAttribute("data-channel").toLowerCase().startsWith(event.target.value.toLowerCase())) ? (element.style.display = "block"): (element.style.display = "none"))
})

replaceElements(block2, input2)


const textAreas = document.getElementsByTagName('textarea');

Array.prototype.forEach.call(textAreas, function(elem) {
    elem.placeholder = elem.placeholder.replace(/\\n/g, '\n');
});