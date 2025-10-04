document.addEventListener('DOMContentLoaded', () => {
  const flashcards = JSON.parse(document.getElementById('flashcards-data').textContent);
  const gradeLevels = JSON.parse(document.getElementById('grade-levels-data').textContent);
  let currentCard = 0;
  let score = 0;

  const cardFront = document.getElementById('card-front');
  const cardBack = document.getElementById('card-back');
  const flashcardElem = document.getElementById('flashcard');
  const prevButton = document.getElementById('prev-btn');
  const nextButton = document.getElementById('next-btn');
  const answerInput = document.getElementById('answer-input');
  const checkButton = document.getElementById('check-answer');
  const giveUpButton = document.getElementById('give-up');
  const scoreDisplay = document.getElementById('score-display');

  const questionInput = document.getElementById('qa-question');
  const askButton = document.getElementById('qa-ask');
  const answerBox = document.getElementById('qa-answer');

  const hintBox = document.createElement('div');
  hintBox.id = 'hint-box';
  document.querySelector('.answer-area').appendChild(hintBox);

  const hintButton = document.createElement('button');
  hintButton.textContent = 'Show Hint';
  hintButton.classList.add('hint-button');
  document.querySelector('.answer-area').appendChild(hintButton);

  const completionMessage = document.getElementById('completion-message');
  const answeredCards = flashcards.map(() => false);
  let isProcessing = false;

  function showCard(cardNumber) {
    currentCard = cardNumber;
    const card = flashcards[currentCard];
    cardFront.textContent = card.question;
    cardBack.textContent = card.answer;
    flashcardElem.classList.remove('flipped');

    prevButton.disabled = currentCard === 0;
    nextButton.disabled = currentCard === flashcards.length - 1;

    answerInput.value = '';
    hintBox.textContent = '';
    answerBox.textContent = '';
    scoreDisplay.textContent = `${score}/${flashcards.length}`;

    checkButton.disabled = answeredCards[currentCard];
    giveUpButton.disabled = answeredCards[currentCard];

    if (completionMessage) completionMessage.style.display = 'none';
  }

  function showCompletion() {
    if (completionMessage) {
      completionMessage.innerHTML = `
        🎉 You finished all the flashcards!<br />
        <strong>Final score: ${score} / ${flashcards.length}</strong><br />
        <a href="/" class="back-button">← Back to Home</a>
      `;
      completionMessage.style.display = 'block';
    }
    flashcardElem.style.display = 'none';
    document.querySelector('.controls').style.display = 'none';
    document.querySelector('.answer-area').style.display = 'none';
  }

  async function submitAnswer(giveUp = false) {
    if (isProcessing || answeredCards[currentCard]) return;
    const userAnswer = answerInput.value.trim();
    if (!userAnswer && !giveUp) return;

    isProcessing = true;
    checkButton.disabled = true;
    giveUpButton.disabled = true;

    const card = flashcards[currentCard];
    const grade = gradeLevels[currentCard];

    if (giveUp) {
      answeredCards[currentCard] = true;
      flashcardElem.classList.add('flipped');
      scoreDisplay.textContent = `${score}/${flashcards.length}`;

      setTimeout(() => {
        if (currentCard < flashcards.length - 1) showCard(currentCard + 1);
        else showCompletion();
        isProcessing = false;
      }, 700);
      return;
    }

    try {
      const res = await fetch('/check_answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_answer: userAnswer,
          correct_answer: card.answer,
          grade_level: grade
        })
      });
      const { correct } = await res.json();

      if (correct) {
        if (!answeredCards[currentCard]) score++;
        answeredCards[currentCard] = true;
        scoreDisplay.textContent = `${score}/${flashcards.length}`;
        flashcardElem.classList.add('flipped');

        setTimeout(() => {
          if (currentCard < flashcards.length - 1) showCard(currentCard + 1);
          else showCompletion();
          isProcessing = false;
        }, 700);
      } else {
        checkButton.disabled = false;
        giveUpButton.disabled = false;
        isProcessing = false;
      }
    } catch (err) {
      console.error(err);
      isProcessing = false;
    }

    prevButton.disabled = currentCard === 0;
    nextButton.disabled = currentCard === flashcards.length - 1;
  }

  checkButton.addEventListener('click', () => submitAnswer(false));
  giveUpButton.addEventListener('click', () => submitAnswer(true));

  hintButton.addEventListener('click', () => {
    hintBox.textContent = `Hint: ${flashcards[currentCard].hint}`;
  });

  askButton.addEventListener('click', async () => {
    const userQ = questionInput.value.trim();
    if (!userQ) return;
    answerBox.textContent = 'Thinking...';
    const res = await fetch('/ask_question', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: userQ,
        flashcard: flashcards[currentCard]
      })
    });
    const { answer } = await res.json();
    answerBox.textContent = answer;
  });

  prevButton.addEventListener('click', () => {
    if (!isProcessing && currentCard > 0) showCard(currentCard - 1);
  });

  nextButton.addEventListener('click', () => {
    if (!isProcessing && currentCard < flashcards.length - 1) showCard(currentCard + 1);
    else if (answeredCards.every(a => a)) showCompletion();
  });

  answerInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') checkButton.click();
  });

  showCard(0);
});
