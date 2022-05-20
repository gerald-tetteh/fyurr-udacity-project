const deleteBtn = document.querySelector("#delete");

deleteBtn.addEventListener("click", async (e) => {
  const response = await fetch(`/artists/${deleteBtn.dataset["id"]}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (response.ok) {
    window.location = "/";
  }
});
