
const dateOptions = document.getElementById("mailing__date__format");
const isInstant = document.getElementById("id_is_instant");
const periodicalDates = document.getElementById("periodical__dates");
const particularDates = document.getElementById("particular__dates");
const optionsSelect = document.getElementById("mailing__date__select")
setTimeout(() => {console.log(document.getElementById("id_is_instant"))}, 100);

isInstant.addEventListener('change', (event) => {
    if (isInstant.checked) {
        dateOptions.style.display = "None";
        periodicalDates.style.display = "none";
        [...periodicalDates.getElementsByTagName('input')].forEach(element => {element.removeAttribute('required')})
        particularDates.style.display = "none";
        [...particularDates.getElementsByTagName('input')].forEach(element => {element.removeAttribute('required')})
        } else {
            dateOptions.style.display = "block";
            periodicalDates.style.display = "block";
            [...periodicalDates.getElementsByTagName('input')].forEach(element => {element.setAttribute('required', 'true')})
        }
    });

dateOptions.addEventListener("change", (event) => {
   if (optionsSelect.value === "periodical") {
                periodicalDates.style.display = "block";
                [...periodicalDates.getElementsByTagName('input')].forEach(element => {element.setAttribute('required', 'true')})
                particularDates.style.display = "none";
                [...particularDates.getElementsByTagName('input')].forEach(element => {element.removeAttribute('required')})
            } else {
                particularDates.style.display = "block";
                [...particularDates.getElementsByTagName('input')].forEach(element => {element.setAttribute('required', 'true')})
                periodicalDates.style.display = "none";
                [...periodicalDates.getElementsByTagName('input')].forEach(element => {element.removeAttribute('required')})
            }
})

